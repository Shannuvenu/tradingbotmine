"""Event-driven bar backtester + chronological validation.

Bias controls:
  * Signals computed at bar t close; fills at bar t+1 OPEN (no same-bar look-ahead).
  * Stops: if the next bar opens through the stop, fill at the open (gap risk modelled);
    else at the stop. If stop and target are both touched in one bar, the stop is assumed
    first (conservative).
  * Indicators are causal (see analytics/indicators.py); Donchian/volume use prior bars only.
  * Costs: full Indian statutory + brokerage model per order (analytics/costs.py) + slippage.
  * Integer share quantities sized from actual capital; trades unaffordable at the
    configured capital are SKIPPED and counted (small-account reality).
  * Splits are chronological (train → validation → out-of-sample test). No shuffling.
Survivorship bias: backtests run on instruments that exist in today's instrument file;
delisted names are absent. Reports state this limitation.
"""
from __future__ import annotations

import itertools
import json
import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from .analytics.costs import CostModel
from .analytics.regime import regime_series
from .analytics.stats import bootstrap_mean_ci, sharpe, sortino
from .data.calendar import parse_hhmm
from .data.validation import data_hash
from .strategies.base import Strategy


@dataclass
class BTConfig:
    capital: float = 1000.0
    risk_per_trade_pct: float = 0.02
    max_exposure_pct: float = 0.8
    slippage_bps: float = 5.0          # per side, applied adversely
    squareoff: str = "15:10"
    exchange: str = "NSE"
    min_trades: int = 30
    max_cost_to_risk_ratio: float | None = 0.5   # mirror the live risk engine; None disables
    min_reward_cost_ratio: float | None = 3.0


@dataclass
class BacktestResult:
    trades: pd.DataFrame
    equity: pd.Series
    metrics: dict
    params: dict
    skipped_unaffordable: int = 0
    skipped_costs: int = 0
    notes: list = field(default_factory=list)


def _segment(style: str) -> str:
    return "EQ_INTRADAY" if style == "intraday" else "EQ_DELIVERY"


def run_backtest(df: pd.DataFrame, strat: Strategy, params: dict | None = None, cfg: BTConfig | None = None,
                 context: dict | None = None, costs: CostModel | None = None) -> BacktestResult:
    cfg = cfg or BTConfig()
    costs = costs or CostModel()
    params = {**strat.params, **(params or {})}
    sig = strat.generate(df, params, context)
    seg = _segment(strat.style)
    intraday = strat.style == "intraday"
    sq = parse_hhmm(cfg.squareoff)
    slip = cfg.slippage_bps / 1e4

    o, h, l, c = (df[x].values for x in ("open", "high", "low", "close"))
    idx = df.index
    dates = np.array([t.date() for t in idx])
    times = np.array([t.time() for t in idx]) if intraday else None
    entry_sig, exit_sig = sig["entry"].values, sig["exit"].values
    stop_sig, tgt_sig, why = sig["stop"].values, sig["target"].values, sig["why"].values

    cash = cfg.capital
    pos = None
    trades, eq = [], np.empty(len(df))
    skipped = 0
    skipped_costs = 0

    def close_pos(i, px, reason):
        nonlocal cash, pos
        fill = px * (1 - slip)
        cb = costs.round_trip(seg, pos["entry"], fill, pos["qty"], True, cfg.exchange)
        gross = (fill - pos["entry"]) * pos["qty"]
        net = gross - cb.total
        cash += fill * pos["qty"] - (cb.total - pos["entry_cost_paid"])
        trades.append({"entry_ts": pos["ts"], "exit_ts": idx[i], "qty": pos["qty"], "entry": pos["entry"],
                       "exit": fill, "stop": pos["stop"], "gross_pnl": gross, "costs": cb.total, "net_pnl": net,
                       "ret_on_capital": net / cfg.capital, "bars_held": i - pos["i"], "exit_reason": reason,
                       "why": pos["why"], "notional": pos["entry"] * pos["qty"]})
        pos = None

    for i in range(len(df)):
        if pos is not None:
            # 1) protective stop / target on this bar
            st, tg = pos["stop"], pos["target"]
            if o[i] <= st:
                close_pos(i, o[i], "stop_gap")
            elif l[i] <= st:
                close_pos(i, st, "stop")
            elif tg is not None and not math.isnan(tg) and h[i] >= tg:
                close_pos(i, max(tg, o[i]), "target")
        if pos is not None and i > 0 and exit_sig[i - 1] and pos["i"] < i:
            close_pos(i, o[i], "exit_signal")
        if pos is not None and intraday:
            last_of_day = (i == len(df) - 1) or (dates[i + 1] != dates[i])
            if times[i] >= sq or last_of_day:
                close_pos(i, c[i], "squareoff")
        # 2) new entry from previous bar's signal, filled at this bar's open
        if pos is None and i > 0 and entry_sig[i - 1]:
            same_day = (not intraday) or dates[i] == dates[i - 1]
            ok_time = (not intraday) or times[i] < sq
            stop = stop_sig[i - 1]
            px = o[i] * (1 + slip)
            if same_day and ok_time and not math.isnan(stop) and stop < px:
                risk_ps = px - stop
                qty = int(min(cfg.capital * cfg.risk_per_trade_pct / risk_ps,
                              cash * cfg.max_exposure_pct / px))
                rt = costs.round_trip(seg, px, px + 2 * risk_ps, qty, True, cfg.exchange).total if qty >= 1 else 0
                cost_bad = qty >= 1 and (
                    (cfg.max_cost_to_risk_ratio is not None and rt > cfg.max_cost_to_risk_ratio * risk_ps * qty)
                    or (cfg.min_reward_cost_ratio is not None and not math.isnan(tgt_sig[i - 1])
                        and (tgt_sig[i - 1] - px) * qty < cfg.min_reward_cost_ratio * rt)
                    or rt >= cash - px * qty)
                if cost_bad:
                    skipped_costs += 1
                elif qty >= 1:
                    ec = costs.order_cost(seg, "BUY", px, qty, cfg.exchange).total
                    cash -= px * qty + ec
                    pos = {"i": i, "ts": idx[i], "entry": px, "qty": qty, "stop": stop,
                           "target": tgt_sig[i - 1], "why": why[i - 1], "entry_cost_paid": ec}
                else:
                    skipped += 1
        eq[i] = cash + (pos["qty"] * c[i] if pos else 0.0)
    if pos is not None:
        close_pos(len(df) - 1, c[-1], "end_of_data")
        eq[-1] = cash

    tr = pd.DataFrame(trades)
    equity = pd.Series(eq, index=idx, name="equity")
    m = compute_metrics(tr, equity, cfg, intraday)
    m["skipped_unaffordable"] = skipped
    m["skipped_cost_filter"] = skipped_costs
    exposure = 0.0
    if len(tr):
        exposure = float(tr["bars_held"].sum() / max(len(df), 1))
    m["exposure"] = round(exposure, 4)
    return BacktestResult(tr, equity, m, params, skipped, skipped_costs)


def compute_metrics(tr: pd.DataFrame, equity: pd.Series, cfg: BTConfig, intraday: bool) -> dict:
    daily = equity.groupby(equity.index.date).last() if intraday else equity
    daily.index = pd.to_datetime(daily.index)
    rets = daily.pct_change().dropna()
    peak = equity.cummax()
    dd = (equity / peak - 1).min() if len(equity) else 0.0
    years = max((daily.index[-1] - daily.index[0]).days / 365.25, 1e-9) if len(daily) > 1 else 0
    total = equity.iloc[-1] / cfg.capital - 1 if len(equity) else 0.0
    m = {"start": str(equity.index[0]) if len(equity) else None, "end": str(equity.index[-1]) if len(equity) else None,
         "net_pnl": round(float(equity.iloc[-1] - cfg.capital), 2) if len(equity) else 0.0,
         "total_return": round(float(total), 4),
         "annualized_return": round(float((1 + total) ** (1 / years) - 1), 4) if years >= 1 and total > -1 else None,
         "max_drawdown": round(float(dd), 4), "sharpe": None, "sortino": None, "trades": int(len(tr))}
    if len(rets) >= 60:
        m["sharpe"] = round(sharpe(rets), 3)
        m["sortino"] = round(sortino(rets), 3)
    if len(tr):
        wins, losses = tr[tr.net_pnl > 0], tr[tr.net_pnl <= 0]
        gp, gl = wins.net_pnl.sum(), -losses.net_pnl.sum()
        ci = bootstrap_mean_ci(tr.net_pnl.values)
        m.update({
            "win_rate": round(len(wins) / len(tr), 4),
            "profit_factor": round(float(gp / gl), 3) if gl > 0 else None,
            "avg_win": round(float(wins.net_pnl.mean()), 2) if len(wins) else 0.0,
            "avg_loss": round(float(losses.net_pnl.mean()), 2) if len(losses) else 0.0,
            "expectancy": round(float(tr.net_pnl.mean()), 3),
            "expectancy_ci95": [round(ci[0], 3), round(ci[1], 3)],
            "gross_pnl": round(float(tr.gross_pnl.sum()), 2),
            "total_costs": round(float(tr.costs.sum()), 2),
            "turnover": round(float((tr.notional * 2).sum()), 2),
            "avg_bars_held": round(float(tr.bars_held.mean()), 2),
            "costs_pct_of_gross_abs": round(float(tr.costs.sum() / max(abs(tr.gross_pnl).sum(), 1e-9)), 3),
        })
    return m


def buy_and_hold(df: pd.DataFrame, cfg: BTConfig | None = None, costs: CostModel | None = None) -> dict:
    cfg = cfg or BTConfig()
    costs = costs or CostModel()
    px = df["open"].iloc[0]
    qty = int(cfg.capital * cfg.max_exposure_pct // px)
    if qty < 1:
        return {"note": "benchmark unaffordable at this capital (1 share > exposure cap)", "total_return": None}
    rt = costs.round_trip("EQ_DELIVERY", px, df["close"].iloc[-1], qty).total
    pnl = (df["close"].iloc[-1] - px) * qty - rt
    eq = cfg.capital + (df["close"] - px) * qty
    return {"total_return": round(float(pnl / cfg.capital), 4), "max_drawdown": round(float((eq / eq.cummax() - 1).min()), 4),
            "qty": qty}


# ------------------------------------------------------------------ validation
def chrono_split(df: pd.DataFrame, train=0.6, val=0.2):
    n = len(df)
    a, b = int(n * train), int(n * (train + val))
    return df.iloc[:a], df.iloc[a:b], df.iloc[b:]


def _grid(strat: Strategy):
    keys = list(strat.param_grid)
    for combo in itertools.product(*[strat.param_grid[k] for k in keys]):
        yield dict(zip(keys, combo))


def _objective(m: dict, min_trades: int) -> float:
    if m["trades"] < max(5, min_trades // 3):
        return -1e9
    return m["net_pnl"] / (1 + abs(m["max_drawdown"]) * 10)


def evaluate_strategy(df: pd.DataFrame, strat: Strategy, cfg: BTConfig | None = None, context: dict | None = None,
                      source: str = "unknown", key: str = "") -> dict:
    """Train→validation→test with grid search on TRAIN only; reports parameter sensitivity and verdict."""
    cfg = cfg or BTConfig()
    tr_df, va_df, te_df = chrono_split(df)
    grid_rows = []
    for p in _grid(strat) or [{}]:
        r = run_backtest(tr_df, strat, p, cfg, context)
        grid_rows.append({"params": p, **{k: r.metrics.get(k) for k in ("net_pnl", "trades", "max_drawdown",
                                                                        "profit_factor", "win_rate")},
                          "score": _objective(r.metrics, cfg.min_trades)})
    if not grid_rows:
        grid_rows = [{"params": {}, "score": 0}]
    best = max(grid_rows, key=lambda x: x["score"])
    bp = best["params"]
    full_tr = run_backtest(tr_df, strat, bp, cfg, context)
    val = run_backtest(va_df, strat, bp, cfg, context)
    test = run_backtest(te_df, strat, bp, cfg, context)
    full = run_backtest(df, strat, bp, cfg, context)
    bench = buy_and_hold(te_df, cfg)
    scores = [g["score"] for g in grid_rows if g["score"] > -1e8]
    pos_frac = float(np.mean([g["net_pnl"] > 0 for g in grid_rows if g.get("net_pnl") is not None])) if grid_rows else 0
    # cost sensitivity on test (0x, 1x, 2x slippage)
    cost_sens = {}
    for mult in (0.0, 1.0, 2.0):
        c2 = BTConfig(**{**cfg.__dict__, "slippage_bps": cfg.slippage_bps * mult})
        cost_sens[f"slippage_x{mult:g}"] = run_backtest(te_df, strat, bp, c2, context).metrics["net_pnl"]
    # regime breakdown (full period)
    reg_perf = {}
    if len(full.trades) and strat.style == "swing":
        rs = regime_series(df)
        lab = rs.reindex(full.trades["entry_ts"]).values
        t = full.trades.assign(regime=lab)
        reg_perf = t.groupby("regime")["net_pnl"].agg(["count", "sum", "mean"]).round(2).to_dict("index")

    flags = []
    tot_trades = full.metrics["trades"]
    if tot_trades < cfg.min_trades:
        flags.append(f"TOO_FEW_TRADES ({tot_trades} < {cfg.min_trades})")
    if test.metrics["net_pnl"] <= 0:
        flags.append("NON_POSITIVE_OUT_OF_SAMPLE")
    if val.metrics["net_pnl"] <= 0:
        flags.append("NON_POSITIVE_VALIDATION")
    g = full.metrics.get("gross_pnl", 0) or 0
    if g > 0 and full.metrics["net_pnl"] <= 0:
        flags.append("EDGE_DISAPPEARS_AFTER_COSTS")
    if pos_frac < 0.5:
        flags.append(f"PARAMETER_INSTABILITY (only {pos_frac:.0%} of grid profitable in train)")
    ci = full.metrics.get("expectancy_ci95")
    if ci and ci[0] <= 0:
        flags.append("EXPECTANCY_CI_INCLUDES_ZERO")
    if full.skipped_costs > tot_trades:
        flags.append(f"COSTS_BLOCK_MOST_SIGNALS ({full.skipped_costs} signals failed the cost filter at "
                     f"capital ₹{cfg.capital:,.0f})")
    if full.skipped_unaffordable > tot_trades:
        flags.append(f"MOSTLY_UNAFFORDABLE ({full.skipped_unaffordable} signals skipped at capital ₹{cfg.capital:,.0f})")
    if source.startswith("SYNTHETIC"):
        flags.append("SYNTHETIC_DATA — results are a software test, not evidence")
    if tot_trades == 0:
        flags.insert(0, "NO_TRADES_AFTER_AFFORDABILITY_AND_COST_FILTERS")
        blocked = full.skipped_costs or full.skipped_unaffordable
        verdict = "NOT_TRADABLE_AT_THIS_CAPITAL" if blocked else "NO_SIGNALS"
    elif not flags:
        verdict = "CANDIDATE"
    elif any(f.startswith(("NON_POSITIVE_OUT", "EDGE_DIS")) for f in flags):
        verdict = "REJECT"
    else:
        verdict = "INSUFFICIENT_EVIDENCE"
    return {
        "run_id": uuid.uuid4().hex[:12], "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "strategy": strat.name, "instrument_key": key, "data_source": source, "data_hash": data_hash(df),
        "period": {"start": str(df.index[0]), "end": str(df.index[-1]), "bars": len(df)},
        "split": {"train": [str(tr_df.index[0]), str(tr_df.index[-1])],
                  "validation": [str(va_df.index[0]), str(va_df.index[-1])],
                  "test": [str(te_df.index[0]), str(te_df.index[-1])]},
        "best_params": bp, "grid": grid_rows, "grid_profitable_fraction": round(pos_frac, 3),
        "train": full_tr.metrics, "validation": val.metrics, "test": test.metrics, "full": full.metrics,
        "benchmark_test_buy_hold": bench, "cost_sensitivity_test": cost_sens, "regime_performance": reg_perf,
        "flags": flags, "verdict": verdict, "equity_full": full.equity, "trades_full": full.trades,
    }


def walk_forward(df: pd.DataFrame, strat: Strategy, cfg: BTConfig | None = None, n_splits: int = 4,
                 context: dict | None = None) -> pd.DataFrame:
    """Anchored walk-forward: optimise on [0, k), test on [k, k+step)."""
    cfg = cfg or BTConfig()
    n = len(df)
    step = n // (n_splits + 1)
    rows = []
    for k in range(1, n_splits + 1):
        tr, te = df.iloc[: k * step], df.iloc[k * step:(k + 1) * step]
        best = max(_grid(strat), key=lambda p: _objective(run_backtest(tr, strat, p, cfg, context).metrics,
                                                         cfg.min_trades), default={})
        m = run_backtest(te, strat, best, cfg, context).metrics
        rows.append({"fold": k, "test_start": str(te.index[0]), "test_end": str(te.index[-1]), "params": json.dumps(best),
                     "net_pnl": m["net_pnl"], "trades": m["trades"], "max_drawdown": m["max_drawdown"]})
    return pd.DataFrame(rows)
