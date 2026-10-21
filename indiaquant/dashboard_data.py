"""Data layer for the Streamlit dashboard (UI-free, unit-testable).

Every function returns real computed values or an explicit "unavailable" reason.
Nothing here fabricates prices or results.
"""
from __future__ import annotations

import json

import pandas as pd

from .analytics import indicators as ind
from .analytics import stockshield
from .analytics.costs import CostModel
from .analytics.options import chain_to_rows
from .analytics.regime import classify
from .broker.upstox import UpstoxError
from .data.calendar import now_ist
from .data.instruments import InstrumentMaster
from .strategies.catalog import REGISTRY


def overview(svc) -> dict:
    st = svc.calendar.status()
    out = {"session": st.phase, "session_detail": st.detail, "ist_time": now_ist().strftime("%Y-%m-%d %H:%M:%S"),
           "exec_state": svc.state.info, "token": bool(svc.token_info),
           "token_expires": (svc.token_info or {}).get("expires_at"), "indices": {}, "account": None,
           "errors": []}
    if not svc.client.has_token:
        out["errors"].append("Not logged in: live quotes, funds and positions unavailable. Run LOGIN.bat.")
        return out
    keys = [svc.settings.benchmark_key, svc.settings.sensex_key, svc.settings.vix_key]
    try:
        q = svc.client.ltp(keys)
        for k in keys:
            if k in q:
                v = q[k]
                cp = v.get("cp") or 0
                out["indices"][k] = {"ltp": v.get("last_price"), "prev_close": cp,
                                     "chg_pct": ((v.get("last_price") or 0) / cp - 1) if cp else None}
    except UpstoxError as e:
        out["errors"].append(f"index quotes: {e}")
    try:
        f = svc.client.funds()["available_to_trade"]["cash_available_to_trade"]
        pos = svc.client.positions()
        out["account"] = {"cash_available": f.get("total"),
                          "realised_today": sum(float(p.get("realised") or 0) for p in pos),
                          "unrealised": sum(float(p.get("unrealised") or 0) for p in pos),
                          "open_positions": sum(1 for p in pos if int(p.get("quantity") or 0) != 0),
                          "exposure": sum(abs(float(p.get("last_price") or 0) * int(p.get("quantity") or 0))
                                          for p in pos)}
    except (UpstoxError, KeyError, TypeError) as e:
        out["errors"].append(f"account: {e}")
    return out


def watchlist_table(svc) -> pd.DataFrame:
    rows = []
    im = InstrumentMaster(svc.db)
    quotes = {}
    if svc.client.has_token:
        try:
            quotes = svc.client.ltp(svc.settings.watchlist)
        except UpstoxError:
            quotes = {}
    for k in svc.settings.watchlist:
        d = svc.db.load_candles(k, "1d")
        ins = im.get(k)
        r = {"instrument_key": k, "symbol": ins.trading_symbol if ins else k}
        q = quotes.get(k)
        if q:
            r["ltp"] = q.get("last_price")
            r["chg_pct"] = (q["last_price"] / q["cp"] - 1) if q.get("cp") else None
        if len(d) >= 60:
            c = d["close"]
            r.update({"last_close": float(c.iloc[-1]), "ret_20d": float(c.pct_change(20).iloc[-1]),
                      "rsi14": float(ind.rsi(c).iloc[-1]), "vol_ratio": float(ind.volume_ratio(d["volume"]).iloc[-1]),
                      "atr_pct": float((ind.atr(d) / c).iloc[-1]), "regime": classify(d).primary,
                      "shield": stockshield.analyze(d).level, "data_source": d["source"].iloc[-1],
                      "affordable_1_share": float(c.iloc[-1]) <= svc.settings.risk.max_order_notional})
        else:
            r["note"] = f"only {len(d)} daily bars stored; run FETCH_HISTORY"
        rows.append(r)
    return pd.DataFrame(rows)


def scanner(svc) -> pd.DataFrame:
    rows = []
    for k in svc.settings.watchlist:
        d = svc.db.load_candles(k, "1d")
        if len(d) < 60:
            continue
        for name, s in REGISTRY.items():
            if s.style != "swing":
                continue
            ctx = {"benchmark": svc.db.load_candles(svc.settings.benchmark_key, "1d")} if s.needs_benchmark else {}
            sig = s.latest_signal(d, k, None, ctx)
            if sig:
                rows.append({"instrument_key": k, "strategy": name, "family": s.family, "bar": sig.bar_ts,
                             "ref_price": sig.entry_ref, "stop": round(sig.stop, 2), "why": sig.explanation})
    return pd.DataFrame(rows)


def intraday_view(svc, key: str) -> dict:
    if not svc.client.has_token:
        return {"error": "login required for intraday candles"}
    try:
        df = svc.client.intraday(key, "minutes", 1)
    except UpstoxError as e:
        return {"error": str(e)}
    if df.empty:
        return {"error": "no intraday candles (market closed or no trades yet today)"}
    df["vwap"] = ind.session_vwap(df)
    orr = ind.opening_range(df, 15)
    df["or_high"], df["or_low"] = orr["or_high"], orr["or_low"]
    df["vol_ratio"] = ind.volume_ratio(df["volume"], 20)
    sigs = {}
    for name, s in REGISTRY.items():
        if s.style == "intraday":
            g = s.generate(df)
            e = g[g["entry"]]
            if len(e):
                sigs[name] = {"last_signal_bar": str(e.index[-1]), "why": e["why"].iloc[-1],
                              "stop": float(e["stop"].iloc[-1])}
    return {"df": df, "signals": sigs}


def cost_preview(price: float, qty: int, product: str) -> dict:
    cm = CostModel()
    seg = "EQ_INTRADAY" if product == "I" else "EQ_DELIVERY"
    rt = cm.round_trip(seg, price, price, qty)
    return {**rt.as_dict(), "breakeven_move_pct": cm.breakeven_move_pct(seg, price, qty)}


def option_chain_view(svc, underlying_key: str, expiry: str) -> dict:
    if not svc.client.has_token:
        return {"error": "login required"}
    try:
        rows = chain_to_rows(svc.client.option_chain(underlying_key, expiry))
    except UpstoxError as e:
        return {"error": str(e)}
    df = pd.DataFrame(rows)
    if df.empty:
        return {"error": "empty chain (check expiry date format YYYY-MM-DD)"}
    im = InstrumentMaster(svc.db)
    lots = {}
    for k in df["instrument_key"].dropna().unique()[:400]:
        ins = im.get(k)
        if ins:
            lots[k] = ins.lot_size
    df["lot_size"] = df["instrument_key"].map(lots)
    df["premium_per_lot"] = df["ltp"] * df["lot_size"]
    cap = svc.settings.risk.starting_capital
    df["affordable"] = df["premium_per_lot"] <= cap * svc.settings.risk.max_capital_exposure_pct
    return {"df": df, "note": "Greeks/IV from Upstox option chain (broker-supplied). Affordability uses premium × lot "
                              "vs. capital; option buying is disabled by default in settings."}


def strategy_lab(svc) -> pd.DataFrame:
    rows = svc.db.query("SELECT run_id, ts, strategy, instrument_key, data_source, metrics FROM backtest_runs "
                        "ORDER BY ts DESC LIMIT 500")
    out = []
    for r in rows:
        m = json.loads(r["metrics"])
        out.append({"ts": r["ts"], "strategy": r["strategy"], "instrument_key": r["instrument_key"],
                    "data_source": r["data_source"], "verdict": m.get("verdict"),
                    "test_net_pnl": (m.get("test") or {}).get("net_pnl"),
                    "test_trades": (m.get("test") or {}).get("trades"),
                    "full_trades": (m.get("full") or {}).get("trades"),
                    "full_costs": (m.get("full") or {}).get("total_costs"),
                    "max_dd": (m.get("full") or {}).get("max_drawdown"), "flags": "; ".join(m.get("flags", [])),
                    "run_id": r["run_id"]})
    return pd.DataFrame(out)


def run_detail(svc, run_id: str) -> dict:
    r = svc.db.query("SELECT metrics FROM backtest_runs WHERE run_id=?", (run_id,))
    return json.loads(r[0]["metrics"]) if r else {}


def execution_tables(svc) -> dict:
    out = {"orders_local": pd.DataFrame(svc.db.query("SELECT client_tag, broker_order_id, instrument_key, side, "
                                                     "quantity, price, order_type, product, status, filled_quantity, "
                                                     "average_price, status_message, strategy, created_at FROM orders "
                                                     "ORDER BY created_at DESC LIMIT 200")),
           "signals": pd.DataFrame(svc.db.query("SELECT ts, instrument_key, strategy, decision, decision_reasons, "
                                                "explanation FROM signals ORDER BY ts DESC LIMIT 200")),
           "audit": pd.DataFrame(svc.db.query("SELECT ts, category, message FROM audit_log ORDER BY id DESC LIMIT 200")),
           "api_errors": pd.DataFrame(svc.db.query("SELECT ts, endpoint, status, message FROM api_errors "
                                                   "ORDER BY id DESC LIMIT 200")),
           "data_quality": pd.DataFrame(svc.db.query("SELECT ts, instrument_key, interval, issue, detail FROM "
                                                     "data_quality ORDER BY id DESC LIMIT 200"))}
    if svc.client.has_token:
        for name, fn in (("positions", svc.client.positions), ("holdings", svc.client.holdings),
                         ("broker_orders", svc.client.order_book), ("trades", svc.client.trades_today)):
            try:
                out[name] = pd.DataFrame(fn())
            except UpstoxError as e:
                out[name] = pd.DataFrame([{"error": str(e)}])
    return out


def shield_report(svc, key: str) -> dict:
    d = svc.db.load_candles(key, "1d")
    if len(d) < 40:
        return {"error": f"need ≥40 daily bars, have {len(d)}"}
    r = stockshield.analyze(d)
    return {"score": r.score, "level": r.level, "contributions": r.contributions, "observed": r.observed,
            "hypotheses": r.hypotheses, "limitations": r.limitations, "df": d}
