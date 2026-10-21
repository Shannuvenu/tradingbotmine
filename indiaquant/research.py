"""Reproducible research pipeline. Produces reports/strategy_report_<date>.md + JSON/CSV.

Data provenance is carried through every result: rows loaded from the DB keep
their `source` column (e.g. upstox_v3_historical). Synthetic data is only used
when explicitly requested (--synthetic) and every output is stamped
SYNTHETIC_TEST_DATA with the verdict forced to non-evidence.
"""
from __future__ import annotations

import json
from datetime import datetime

import numpy as np
import pandas as pd

from .analytics import ml, stockshield
from .analytics.costs import CostModel
from .analytics.regime import classify
from .analytics.stats import engle_granger
from .backtest import BTConfig, evaluate_strategy, walk_forward
from .config import REPORT_DIR
from .data.calendar import IST
from .data.validation import synthetic_intraday, synthetic_ohlcv, validate_candles
from .logging_setup import get_logger
from .strategies.catalog import REGISTRY

log = get_logger("research")


def _source(df: pd.DataFrame) -> str:
    if df.attrs.get("source"):
        return df.attrs["source"]
    if "source" in df.columns and len(df):
        return str(df["source"].iloc[-1])
    return "unknown"


def md_table(df: pd.DataFrame) -> str:
    """Markdown table without the optional `tabulate` dependency."""
    if df is None or not len(df):
        return "_no rows_"
    cols = [str(c) for c in df.columns]
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        out.append("| " + " | ".join("" if pd.isna(v) else str(v).replace("|", "/") for v in r.values) + " |")
    return "\n".join(out)


def gap_statistics(daily: pd.DataFrame) -> dict:
    gap = daily["open"] / daily["close"].shift() - 1
    filled_up = (daily["low"] <= daily["close"].shift()) & (gap > 0.005)
    filled_dn = (daily["high"] >= daily["close"].shift()) & (gap < -0.005)
    up, dn = gap > 0.005, gap < -0.005
    intraday_ret = daily["close"] / daily["open"] - 1
    return {"n_days": int(gap.notna().sum()), "gap_up_days": int(up.sum()), "gap_down_days": int(dn.sum()),
            "gap_up_fill_rate": round(float(filled_up.sum() / max(up.sum(), 1)), 3),
            "gap_down_fill_rate": round(float(filled_dn.sum() / max(dn.sum(), 1)), 3),
            "mean_open_to_close_after_gap_up": round(float(intraday_ret[up].mean()), 5) if up.any() else None,
            "mean_open_to_close_after_gap_down": round(float(intraday_ret[dn].mean()), 5) if dn.any() else None,
            "max_abs_gap": round(float(gap.abs().max()), 4)}


def time_of_day_profile(intraday: pd.DataFrame, bucket: str = "30min") -> pd.DataFrame:
    r = np.log(intraday["close"]).diff()
    same = pd.Series(intraday.index.date, index=intraday.index)
    r = r.where(same == same.shift())
    step = int(pd.Timedelta(bucket).total_seconds() // 60)
    mins = [(x.hour * 60 + x.minute) // step * step for x in intraday.index]
    b = [f"{m // 60:02d}:{m % 60:02d}" for m in mins]
    g = pd.DataFrame({"r": r.values, "b": b, "v": intraday["volume"].values}).groupby("b")
    return pd.DataFrame({"mean_ret_bps": g["r"].mean() * 1e4, "vol_bps": g["r"].std() * 1e4,
                         "avg_volume": g["v"].mean()}).round(3)


def cross_sectional_momentum(closes: dict[str, pd.Series], lookback=126, skip=21) -> pd.DataFrame:
    rows = []
    for k, s in closes.items():
        if len(s) > lookback + skip:
            rows.append({"instrument_key": k, "mom_12_1": float(s.iloc[-skip] / s.iloc[-lookback - skip] - 1),
                         "ret_1m": float(s.iloc[-1] / s.iloc[-skip] - 1)})
    df = pd.DataFrame(rows)
    return df.sort_values("mom_12_1", ascending=False).reset_index(drop=True) if len(df) else df


def pairs_scan(closes: dict[str, pd.Series], max_pairs: int = 45) -> pd.DataFrame:
    keys = list(closes)
    rows = []
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            if len(rows) >= max_pairs:
                break
            a, b = closes[keys[i]], closes[keys[j]]
            n = len(a.index.intersection(b.index))
            if n < 250:
                continue
            # test on the first 70% only; the rest is held out to check stability
            idx = a.index.intersection(b.index)
            cut = idx[int(len(idx) * 0.7)]
            r_in = engle_granger(a[:cut], b[:cut])
            r_out = engle_granger(a[cut:], b[cut:])
            rows.append({"a": keys[i], "b": keys[j], "t_in": r_in.get("t_stat"), "coint_in": r_in.get("cointegrated"),
                         "t_out": r_out.get("t_stat"), "coint_out": r_out.get("cointegrated"),
                         "hedge_ratio": r_in.get("hedge_ratio"), "half_life": r_in.get("half_life_bars")})
    return pd.DataFrame(rows)


def cross_venue_arbitrage(nse_quote: dict, bse_quote: dict, qty: int, costs: CostModel | None = None) -> dict:
    """Executable economics for buying on one venue and selling on the other (same ISIN, intraday).
    Uses bid/ask, not LTP. Feasibility caveats are returned with the numbers."""
    costs = costs or CostModel()
    out = {}
    for buy_v, sell_v, bq, sq in (("NSE", "BSE", nse_quote, bse_quote), ("BSE", "NSE", bse_quote, nse_quote)):
        ask, bid = bq.get("ask"), sq.get("bid")
        if not ask or not bid:
            out[f"buy_{buy_v}_sell_{sell_v}"] = {"feasible": False, "why": "missing bid/ask"}
            continue
        c = (costs.order_cost("EQ_INTRADAY", "BUY", ask, qty, buy_v).total +
             costs.order_cost("EQ_INTRADAY", "SELL", bid, qty, sell_v).total)
        gross = (bid - ask) * qty
        depth_ok = (bq.get("ask_qty") or 0) >= qty and (sq.get("bid_qty") or 0) >= qty
        out[f"buy_{buy_v}_sell_{sell_v}"] = {"gross": round(gross, 2), "costs": round(c, 2),
                                            "net": round(gross - c, 2), "depth_ok": depth_ok,
                                            "feasible": bool(gross - c > 0 and depth_ok)}
    out["caveats"] = ["Two legs execute separately: leg risk if one fills and the other does not.",
                      "Cross-exchange intraday netting must be supported by the broker; verify before use.",
                      "Quotes are snapshots; latency from a home PC is typically far slower than co-located HFT."]
    return out


def load_or_synthetic(db, key: str, interval: str, synthetic: bool, seed: int = 0) -> pd.DataFrame:
    if synthetic:
        df = synthetic_intraday(30, seed) if interval == "1m" else synthetic_ohlcv(1500, seed)
        df.attrs["source"] = "SYNTHETIC_TEST_DATA"
        return df
    df = db.load_candles(key, interval)
    if len(df):
        df.attrs["source"] = _source(df)
    return df


def run_research(db, settings, synthetic: bool = False, keys: list[str] | None = None,
                 strategies: list[str] | None = None, capital: float | None = None) -> dict:
    keys = keys or settings.watchlist
    strategies = strategies or list(REGISTRY)
    cfg = BTConfig(capital=capital or settings.risk.starting_capital,
                   risk_per_trade_pct=settings.risk.max_risk_per_trade_pct,
                   max_exposure_pct=settings.risk.max_capital_exposure_pct,
                   squareoff=settings.risk.intraday_squareoff_time)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(IST).strftime("%Y%m%d_%H%M")
    results, summary_rows, extras = [], [], {}
    bench = load_or_synthetic(db, settings.benchmark_key, "1d", synthetic, seed=99)
    closes = {}
    for ki, key in enumerate(keys):
        daily = load_or_synthetic(db, key, "1d", synthetic, seed=ki)
        intra = load_or_synthetic(db, key, "1m", synthetic, seed=ki)
        if len(daily):
            closes[key] = daily["close"]
            q = validate_candles(daily, "1d")
            extras.setdefault("data_quality", {})[key] = q.issues
            extras.setdefault("gaps", {})[key] = gap_statistics(daily)
            extras.setdefault("regime_now", {})[key] = classify(daily).labels if len(daily) > 60 else ["UNCERTAIN"]
            sh = stockshield.analyze(daily)
            extras.setdefault("stockshield", {})[key] = {"score": sh.score, "level": sh.level,
                                                        "contributions": sh.contributions}
            extras.setdefault("ml", {})[key] = {"volatility": ml.evaluate_volatility(daily),
                                               "adverse": ml.evaluate_adverse(daily)}
        if len(intra) > 375 * 3:
            extras.setdefault("time_of_day", {})[key] = time_of_day_profile(intra).to_dict("index")
        for name in strategies:
            strat = REGISTRY[name]
            df = intra if strat.style == "intraday" else daily
            need = 375 * 10 if strat.style == "intraday" else 300
            if df is None or len(df) < need:
                summary_rows.append({"instrument_key": key, "strategy": name, "verdict": "NO_DATA",
                                     "flags": f"needs >= {need} bars of {strat.timeframe} data; have {len(df)}"})
                continue
            ctx = {"benchmark": bench} if strat.needs_benchmark else {}
            try:
                ev = evaluate_strategy(df, strat, cfg, ctx, source=df.attrs.get("source", "unknown"), key=key)
            except Exception as e:  # keep the pipeline going, record failure
                log.exception("evaluation failed %s %s", key, name)
                summary_rows.append({"instrument_key": key, "strategy": name, "verdict": "ERROR", "flags": str(e)})
                continue
            if strat.style == "swing":
                ev["walk_forward"] = walk_forward(df, strat, cfg, 4, ctx).to_dict("records")
            store = {k: v for k, v in ev.items() if k not in ("equity_full", "trades_full")}
            db.save_backtest({"run_id": ev["run_id"], "ts": ev["ts"], "strategy": name, "instrument_key": key,
                              "params": json.dumps(ev["best_params"]), "period": json.dumps(ev["period"]),
                              "split": json.dumps(ev["split"]), "metrics": json.dumps(store, default=str),
                              "data_source": ev["data_source"], "data_hash": ev["data_hash"]})
            t = ev["test"]
            summary_rows.append({"instrument_key": key, "strategy": name, "verdict": ev["verdict"],
                                 "trades_full": ev["full"]["trades"], "test_net_pnl": t["net_pnl"],
                                 "test_trades": t["trades"], "test_maxdd": t["max_drawdown"],
                                 "full_net_pnl": ev["full"]["net_pnl"], "full_costs": ev["full"].get("total_costs"),
                                 "skipped_unaffordable": ev["full"].get("skipped_unaffordable"),
                                 "skipped_cost_filter": ev["full"].get("skipped_cost_filter"),
                                 "flags": "; ".join(ev["flags"])})
            results.append(store)
    if len(closes) >= 3:
        extras["cross_sectional_momentum"] = cross_sectional_momentum(closes).to_dict("records")
        extras["pairs"] = pairs_scan(closes).to_dict("records")
    summary = pd.DataFrame(summary_rows)
    report = write_report(summary, extras, stamp, synthetic, cfg)
    return {"summary": summary, "results": results, "extras": extras, "report_path": str(report)}


def write_report(summary: pd.DataFrame, extras: dict, stamp: str, synthetic: bool, cfg: BTConfig):
    p = REPORT_DIR / f"strategy_report_{stamp}{'_SYNTHETIC' if synthetic else ''}.md"
    lines = [f"# INDIA QUANT — Strategy research report ({stamp} IST)", ""]
    if synthetic:
        lines += ["> **SYNTHETIC TEST DATA.** These numbers come from a random-walk generator and exist only to "
                  "exercise the software. They are NOT evidence about any strategy or market.", ""]
    else:
        lines += ["> Historical backtest results on data downloaded from Upstox Historical Candle API V3. "
                  "Past performance does not predict future results. Survivorship bias: only currently-listed "
                  "instruments are tested.", ""]
    lines += [f"Capital ₹{cfg.capital:,.0f}; risk/trade {cfg.risk_per_trade_pct:.1%}; slippage {cfg.slippage_bps} bps/side;"
              f" costs per Upstox published schedule (Oct 2026). Splits: 60% train / 20% validation / 20% test "
              "(chronological). Parameters chosen on train only.", ""]
    n_c = int((summary.get("verdict") == "CANDIDATE").sum()) if len(summary) else 0
    lines += ["## Bottom line", "",
              (f"{n_c} instrument/strategy combinations passed every check." if n_c else
               "**No strategy passed all validation checks → the system recommends NO TRADE.**"), ""]
    lines += ["## Summary", "", md_table(summary) if len(summary) else "_no results_", ""]
    for sec in ("gaps", "regime_now", "stockshield"):
        if sec in extras:
            lines += [f"## {sec}", "", "```json", json.dumps(extras[sec], indent=1, default=str)[:20000], "```", ""]
    if "ml" in extras:
        lines += ["## Machine learning vs baselines", ""]
        for k, v in extras["ml"].items():
            vol, adv = v["volatility"], v["adverse"]
            lines.append(f"- {k}: volatility → {vol.get('decision', vol.get('status'))}; "
                         f"adverse-move → {adv.get('decision', adv.get('status'))}")
        lines.append("")
    for sec in ("cross_sectional_momentum", "pairs"):
        if extras.get(sec):
            lines += [f"## {sec}", "", md_table(pd.DataFrame(extras[sec]).round(4)), ""]
    p.write_text("\n".join(lines), encoding="utf-8")
    summary.to_csv(p.with_suffix(".csv"), index=False)
    return p
