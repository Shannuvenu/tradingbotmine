"""INDIA QUANT — local Streamlit terminal.  Run: RUN_DASHBOARD.bat  (binds to 127.0.0.1 only)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from indiaquant import dashboard_data as dd  # noqa: E402
from indiaquant.app import build, readiness_checks  # noqa: E402
from indiaquant.data.instruments import InstrumentMaster  # noqa: E402
from indiaquant.execution.engine import TradingEngine  # noqa: E402
from indiaquant.execution.state import CONFIRM_PHRASE, StateError  # noqa: E402
from indiaquant.strategies.catalog import REGISTRY  # noqa: E402

st.set_page_config(page_title="INDIA QUANT", page_icon="📈", layout="wide")


@st.cache_resource
def services():
    return build()


svc = services()


def candle_fig(df: pd.DataFrame, overlays: dict | None = None, title: str = ""):
    fig = go.Figure(go.Candlestick(x=df.index, open=df["open"], high=df["high"], low=df["low"], close=df["close"],
                                   name="price"))
    for name, s in (overlays or {}).items():
        fig.add_trace(go.Scatter(x=s.index, y=s.values, name=name, mode="lines", line={"width": 1}))
    fig.update_layout(height=460, margin={"l": 10, "r": 10, "t": 30, "b": 10}, title=title,
                      xaxis_rangeslider_visible=False)
    return fig


def fmt_inr(x):
    return "—" if x is None else f"₹{x:,.2f}"


# ------------------------------------------------------------------ header
state = svc.state.info
c1, c2, c3, c4 = st.columns(4)
c1.markdown("## INDIA QUANT")
c2.metric("Execution state", state.get("state"))
c3.metric("Session", svc.calendar.status().phase)
c4.metric("Upstox login", "valid" if svc.token_info else "required")
if state.get("state") == "LIVE_ACTIVE":
    st.error("LIVE TRADING ACTIVE — real orders can be placed.")
elif state.get("state") == "HALTED":
    st.warning(f"HALTED: {state.get('reason')}")

tabs = st.tabs(["Overview", "Scanner", "Intraday", "Swing", "Futures & Options", "Strategy Lab",
                "Portfolio & Execution", "StockShield", "Reports"])

# ---------------------------------------------------------------- Overview
with tabs[0]:
    ov = dd.overview(svc)
    for e in ov["errors"]:
        st.info(e)
    cols = st.columns(3)
    for i, (k, v) in enumerate(ov["indices"].items()):
        chg = v.get("chg_pct")
        cols[i % 3].metric(k.split("|")[1], f"{v['ltp']:,.2f}" if v.get("ltp") else "—",
                           f"{chg:+.2%}" if chg is not None else None)
    if ov["account"]:
        a = ov["account"]
        cc = st.columns(5)
        cc[0].metric("Cash available", fmt_inr(a["cash_available"]))
        cc[1].metric("Realised today", fmt_inr(a["realised_today"]))
        cc[2].metric("Unrealised", fmt_inr(a["unrealised"]))
        cc[3].metric("Open positions", a["open_positions"])
        cc[4].metric("Exposure", fmt_inr(a["exposure"]))
    st.caption(f"IST {ov['ist_time']} · token expires {ov['token_expires'] or '—'} · {ov['session_detail']}")
    st.subheader("Watchlist")
    st.dataframe(dd.watchlist_table(svc), width="stretch")
    r = svc.settings.risk
    st.subheader("Risk limits in force")
    st.json({"max_risk_per_trade": f"{r.max_risk_per_trade_pct:.1%}", "max_daily_loss": f"{r.max_daily_loss_pct:.1%}",
             "max_open_positions": r.max_open_positions, "max_order_notional": r.max_order_notional,
             "derivatives": r.allow_derivatives, "short": r.allow_short})
    last = svc.db.get_state("last_cycle")
    if last:
        st.caption("Last engine cycle")
        st.json(last)

# ----------------------------------------------------------------- Scanner
with tabs[1]:
    st.subheader("Instrument search (NSE/BSE)")
    q = st.text_input("Symbol / name / ISIN", "")
    if q:
        st.dataframe(InstrumentMaster(svc.db).search(q), width="stretch")
    st.subheader("Swing-strategy signals on latest daily bar")
    sc = dd.scanner(svc)
    st.dataframe(sc if len(sc) else pd.DataFrame([{"result": "no signals (or no daily data stored)"}]),
                 width="stretch")
    st.caption("A signal is not an order: the research gate, regime gate, STOCKSHIELD and risk engine all apply.")

# ---------------------------------------------------------------- Intraday
with tabs[2]:
    key = st.selectbox("Instrument", svc.settings.watchlist, key="intra_key")
    iv = dd.intraday_view(svc, key)
    if "error" in iv:
        st.info(iv["error"])
    else:
        df = iv["df"]
        st.plotly_chart(candle_fig(df, {"VWAP": df["vwap"], "OR high": df["or_high"], "OR low": df["or_low"]}),
                        width="stretch")
        st.json(iv["signals"] or {"signals": "none today"})
    st.subheader("Cost preview")
    cc = st.columns(3)
    price = cc[0].number_input("Price ₹", min_value=0.05, value=400.0)
    qty = cc[1].number_input("Quantity", min_value=1, value=1, step=1)
    prod = cc[2].selectbox("Product", ["I", "D"])
    st.json(dd.cost_preview(price, int(qty), prod))

# ------------------------------------------------------------------- Swing
with tabs[3]:
    key = st.selectbox("Instrument", svc.settings.watchlist, key="swing_key")
    d = svc.db.load_candles(key, "1d")
    if len(d) < 60:
        st.info(f"{len(d)} daily bars stored. Run FETCH_HISTORY.bat after login.")
    else:
        from indiaquant.analytics import indicators as ind
        from indiaquant.analytics.regime import classify
        view = d.tail(400)
        lo, hi = ind.donchian(d, 20)
        st.plotly_chart(candle_fig(view, {"SMA50": ind.sma(d["close"], 50).tail(400),
                                          "SMA200": ind.sma(d["close"], 200).tail(400),
                                          "20d high": hi.tail(400), "20d low": lo.tail(400)}),
                        width="stretch")
        bench = svc.db.load_candles(svc.settings.benchmark_key, "1d")
        rs = ind.relative_strength(d["close"], bench["close"], 63).iloc[-1] if len(bench) else None
        reg = classify(d)
        w = d["close"].resample("W").last()
        st.json({"regime": reg.labels, "features": reg.features,
                 "weekly_trend_up": bool(w.iloc[-1] > w.rolling(10).mean().iloc[-1]),
                 "rel_strength_63d_vs_nifty": None if rs is None or pd.isna(rs) else round(float(rs), 4),
                 "atr14": round(float(ind.atr(d).iloc[-1]), 2), "support_60d": float(d["low"].tail(60).min()),
                 "resistance_60d": float(d["high"].tail(60).max())})

# ---------------------------------------------------------- Futures & Options
with tabs[4]:
    st.subheader("Contracts")
    und = st.text_input("Underlying symbol (e.g. NIFTY, RELIANCE)", "NIFTY").upper()
    im = InstrumentMaster(svc.db)
    exps = im.expiries(und)
    st.write("Expiries:", exps[:12] or "none in instrument master (run SYNC_INSTRUMENTS)")
    fut = im.contracts(und, "FUT")
    if len(fut):
        st.dataframe(fut[["instrument_key", "trading_symbol", "expiry", "lot_size", "tick_size", "freeze_quantity"]],
                     width="stretch")
    st.subheader("Option chain")
    ukey = st.text_input("Underlying instrument_key", "NSE_INDEX|Nifty 50")
    exp = st.text_input("Expiry (YYYY-MM-DD)", exps[0] if exps else "")
    if st.button("Load chain") and exp:
        oc = dd.option_chain_view(svc, ukey, exp)
        if "error" in oc:
            st.info(oc["error"])
        else:
            st.caption(oc["note"])
            st.dataframe(oc["df"], width="stretch")
    st.caption("F&O is disabled by default (allow_derivatives=false). With ₹1,000 most contracts are unaffordable; "
               "the risk engine rejects them rather than switching instrument.")

# ------------------------------------------------------------- Strategy Lab
with tabs[5]:
    st.subheader("Strategy catalogue")
    st.dataframe(pd.DataFrame([{k: v for k, v in s.describe().items() if k not in ("param_grid",)}
                               for s in REGISTRY.values()]), width="stretch")
    st.subheader("Backtest runs")
    lab = dd.strategy_lab(svc)
    if not len(lab):
        st.info("No research runs yet. Run RUN_RESEARCH.bat after FETCH_HISTORY.bat.")
    else:
        st.dataframe(lab, width="stretch")
        rid = st.selectbox("Inspect run", lab["run_id"])
        det = dd.run_detail(svc, rid)
        if det.get("data_source", "").startswith("SYNTHETIC"):
            st.warning("SYNTHETIC TEST DATA — not evidence.")
        st.json({k: det.get(k) for k in ("verdict", "flags", "best_params", "train", "validation", "test",
                                         "benchmark_test_buy_hold", "cost_sensitivity_test", "regime_performance",
                                         "walk_forward")})
        grid = pd.DataFrame(det.get("grid") or [])
        if len(grid):
            st.caption("Parameter sensitivity (train period)")
            st.dataframe(grid, width="stretch")

# --------------------------------------------------- Portfolio & Execution
with tabs[6]:
    t = dd.execution_tables(svc)
    for name in ("positions", "holdings", "broker_orders", "trades"):
        if name in t:
            st.subheader(name.replace("_", " ").title())
            st.dataframe(t[name], width="stretch")
    st.subheader("Local order ledger")
    st.dataframe(t["orders_local"], width="stretch")
    st.subheader("Signal decisions")
    st.dataframe(t["signals"], width="stretch")

    st.divider()
    st.subheader("Controls")
    k1, k2, k3 = st.columns(3)
    if k1.button("🛑 EMERGENCY STOP (halt + cancel pending)", type="primary"):
        eng = TradingEngine(svc.settings, svc.db, svc.client, svc.state, svc.calendar)
        try:
            st.write(eng.kill_switch("dashboard emergency stop", flatten=False))
        except Exception as e:
            svc.state.halt("dashboard emergency stop (broker call failed)")
            st.error(f"Halted, but cancel failed: {e}. Cancel manually in the Upstox app.")
    flat_ok = k2.checkbox("I understand liquidation sells at marketable limit prices, may fill partially, "
                          "and realises P&L")
    if k2.button("Liquidate all long positions", disabled=not flat_ok):
        from indiaquant.data.feed import LiveFeed
        feed = LiveFeed(svc.client, svc.settings.watchlist, use_websocket=False)
        try:
            feed.poll_once()
            eng = TradingEngine(svc.settings, svc.db, svc.client, svc.state, svc.calendar, feed)
            st.write(eng.kill_switch("dashboard liquidation", flatten=True))
        except Exception as e:
            st.error(f"Liquidation failed: {e}. Exit manually in the Upstox app.")
    if k3.button("Run readiness checks → LIVE_READY"):
        checks = readiness_checks(svc)
        st.json(checks)
        try:
            svc.state.mark_live_ready(checks)
            st.success("LIVE_READY (orders still disabled until activation)")
        except StateError as e:
            st.error(str(e))
    with st.expander("Activate live trading (today only)"):
        st.warning("Real money. Losses can exceed modelled stops. Activation expires at the end of today (IST).")
        phrase = st.text_input(f"Type exactly: {CONFIRM_PHRASE}")
        if st.button("Activate LIVE_ACTIVE"):
            try:
                svc.state.activate_live(phrase, operator="dashboard")
                st.success("LIVE_ACTIVE. Start RUN_LIVE.bat to run the engine.")
            except StateError as e:
                st.error(str(e))
    with st.expander("Resume from HALTED"):
        ack = st.text_input("Acknowledge why it halted and what you checked")
        if st.button("Resume to LIVE_READY"):
            try:
                svc.state.resume(ack)
                st.success("Resumed to LIVE_READY")
            except StateError as e:
                st.error(str(e))

# -------------------------------------------------------------- StockShield
with tabs[7]:
    key = st.selectbox("Instrument", svc.settings.watchlist, key="shield_key")
    sr = dd.shield_report(svc, key)
    if "error" in sr:
        st.info(sr["error"])
    else:
        st.metric("Retail-risk score (heuristic, uncalibrated)", f"{sr['score']}/100", sr["level"])
        st.bar_chart(pd.Series(sr["contributions"]))
        st.markdown("**Observed (measured)**")
        st.json(sr["observed"])
        st.markdown("**Possible explanations (hypotheses, not findings)**")
        for h in sr["hypotheses"] or ["No pattern-based hypotheses triggered."]:
            st.write("- " + h)
        st.markdown("**Limitations**")
        for lim in sr["limitations"]:
            st.write("- " + lim)

# ----------------------------------------------------------------- Reports
with tabs[8]:
    from indiaquant.config import REPORT_DIR
    reps = sorted(REPORT_DIR.glob("*.md"), reverse=True)
    if reps:
        sel = st.selectbox("Report", [r.name for r in reps])
        st.markdown((REPORT_DIR / sel).read_text(encoding="utf-8"))
    else:
        st.info("No reports yet.")
    t = dd.execution_tables(svc)
    st.subheader("API errors")
    st.dataframe(t["api_errors"], width="stretch")
    st.subheader("Data quality issues")
    st.dataframe(t["data_quality"], width="stretch")
    st.subheader("Audit log")
    st.dataframe(t["audit"], width="stretch")
