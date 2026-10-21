"""Unit tests. All market data here is SYNTHETIC TEST DATA (clearly generated, never real prices)."""
import gzip
import json
import logging
import os
import tempfile
import time
import unittest
from datetime import datetime, time as dtime
from pathlib import Path

import numpy as np
import pandas as pd

from indiaquant.analytics import indicators as ind
from indiaquant.analytics.costs import CostModel
from indiaquant.analytics.options import bs_price, greeks, implied_vol
from indiaquant.analytics.regime import classify
from indiaquant.analytics.stats import engle_granger
from indiaquant.analytics import stockshield
from indiaquant.backtest import BTConfig, chrono_split, run_backtest
from indiaquant.broker.auth import token_expiry
from indiaquant.broker.ratelimit import SlidingWindowLimiter
from indiaquant.broker.upstox import OrderRejected, OrderRequest, UpstoxClient, AuthExpired, OrderStatusUnknown
from indiaquant.config import RiskLimits, Settings, validate_settings
from indiaquant.data.calendar import IST, MarketCalendar, to_ist
from indiaquant.data.feed import QuoteBook, Quote
from indiaquant.data.instruments import InstrumentMaster, normalize_record, parse_bod_bytes, round_to_tick
from indiaquant.data.validation import clean_candles, is_fresh, synthetic_intraday, synthetic_ohlcv, validate_candles
from indiaquant.db import Database
from indiaquant.execution.orders import DuplicateOrder, OrderManager, make_tag, map_broker_status, reconcile_positions
from indiaquant.execution.risk import AccountSnapshot, OrderIntent, RiskEngine
from indiaquant.execution.state import CONFIRM_PHRASE, ExecutionState, StateError
from indiaquant.logging_setup import RedactingFilter, redact
from indiaquant.strategies.catalog import REGISTRY
from tests.fakes import FakeClient, eq_instrument, quote


def mem_db():
    return Database(":memory:")


# 1. instrument normalization
class TestInstruments(unittest.TestCase):
    RAW = [
        {"segment": "NSE_EQ", "name": "JOCIL LIMITED", "exchange": "NSE", "isin": "INE839G01010", "instrument_type": "EQ",
         "instrument_key": "NSE_EQ|INE839G01010", "lot_size": 1, "freeze_quantity": 100000.0, "exchange_token": "16927",
         "tick_size": 5.0, "trading_symbol": "JOCIL", "short_name": "JOCIL", "security_type": "NORMAL"},
        {"weekly": False, "segment": "NSE_FO", "name": "VODAFONE IDEA LIMITED", "exchange": "NSE",
         "expiry": 1706207399000, "instrument_type": "CE", "underlying_symbol": "IDEA", "instrument_key": "NSE_FO|36708",
         "lot_size": 80000, "freeze_quantity": 1600000.0, "exchange_token": "36708", "minimum_lot": 80000,
         "underlying_key": "NSE_EQ|INE669E01016", "tick_size": 5.0, "underlying_type": "EQUITY",
         "trading_symbol": "IDEA 22 CE 25 JAN 24", "strike_price": 22.0},
        {"segment": "BSE_EQ", "name": "JOCIL LIMITED", "exchange": "BSE", "isin": "INE839G01010", "instrument_type": "A",
         "instrument_key": "BSE_EQ|INE839G01010", "lot_size": 1, "tick_size": 5.0, "trading_symbol": "JOCIL"},
        {"segment": "MCX_FO", "instrument_key": "MCX_FO|1", "instrument_type": "FUT"},
    ]

    def test_normalize(self):
        eq = normalize_record(self.RAW[0])
        self.assertEqual(eq.tick_size, 0.05)        # paise -> rupees
        self.assertFalse(eq.is_derivative)
        opt = normalize_record(self.RAW[1])
        self.assertEqual(opt.option_type, "CE")
        self.assertEqual(opt.strike, 22.0)
        self.assertEqual(opt.expiry, "2024-01-25")  # epoch ms -> IST date
        self.assertEqual(opt.lot_size, 80000)
        self.assertIsNone(normalize_record(self.RAW[3]))  # MCX unsupported

    def test_parse_gz_and_store_nse_bse_distinct(self):
        blob = gzip.compress(json.dumps(self.RAW).encode())
        ins = parse_bod_bytes(blob)
        self.assertEqual(len(ins), 3)
        db = mem_db()
        im = InstrumentMaster(db)
        im.store(ins)
        both = im.by_isin("INE839G01010")
        self.assertEqual({i.instrument_key for i in both}, {"NSE_EQ|INE839G01010", "BSE_EQ|INE839G01010"})
        self.assertEqual(len(im.search("JOCIL")), 2)

    def test_tick_rounding(self):
        self.assertAlmostEqual(round_to_tick(100.03, 0.05, "up"), 100.05)
        self.assertAlmostEqual(round_to_tick(100.03, 0.05, "down"), 100.0)


# 2. candle validation
class TestValidation(unittest.TestCase):
    def test_detects_bad_rows(self):
        df = synthetic_ohlcv(100, 1)
        bad = df.copy()
        bad.iloc[5, bad.columns.get_loc("high")] = bad.iloc[5]["low"] - 1
        bad = pd.concat([bad, bad.iloc[[10]]]).sort_index()
        rep = validate_candles(bad)
        kinds = {k for k, _ in rep.issues}
        self.assertIn("ohlc_inconsistent", kinds)
        self.assertIn("duplicates", kinds)
        self.assertFalse(rep.ok)
        clean = clean_candles(bad)
        self.assertTrue(validate_candles(clean).ok)
        self.assertFalse(clean.index.duplicated().any())

    def test_intraday_gap_detection(self):
        df = synthetic_intraday(2, 0)
        df = df.drop(df.index[50:60])
        kinds = {k for k, _ in validate_candles(df, "1m").issues}
        self.assertIn("intraday_gaps", kinds)


# 3. timezone & sessions
class TestCalendar(unittest.TestCase):
    def test_sessions(self):
        db = mem_db()
        cal = MarketCalendar(db)
        cal.store_holidays([{"date": "2026-10-20", "holiday_type": "TRADING_HOLIDAY", "description": "Diwali (test)",
                             "closed_exchanges": ["NSE", "BSE"], "open_exchanges": []}])
        st = cal.status(datetime(2026, 10, 21, 10, 0, tzinfo=IST))
        self.assertEqual(st.phase, "OPEN")
        self.assertEqual(cal.status(datetime(2026, 10, 21, 9, 5, tzinfo=IST)).phase, "PRE_OPEN")
        self.assertEqual(cal.status(datetime(2026, 10, 21, 15, 30, tzinfo=IST)).phase, "CLOSED")
        self.assertEqual(cal.status(datetime(2026, 10, 20, 11, 0, tzinfo=IST)).phase, "CLOSED_HOLIDAY")
        self.assertEqual(cal.status(datetime(2026, 10, 24, 11, 0, tzinfo=IST)).phase, "CLOSED_WEEKEND")

    def test_unknown_without_holidays(self):
        st = MarketCalendar(mem_db()).status(datetime(2026, 10, 21, 10, 0, tzinfo=IST))
        self.assertEqual(st.phase, "UNKNOWN_HOLIDAY_DATA")
        self.assertFalse(st.is_open)

    def test_utc_conversion(self):
        t = to_ist(pd.Timestamp("2026-10-21T04:00:00Z"))
        self.assertEqual((t.hour, t.minute), (9, 30))

    def test_token_expiry(self):
        e = token_expiry(datetime(2026, 10, 20, 20, 0, tzinfo=IST))
        self.assertEqual(e, datetime(2026, 10, 21, 3, 30, tzinfo=IST))
        e2 = token_expiry(datetime(2026, 10, 21, 2, 30, tzinfo=IST))
        self.assertEqual(e2, datetime(2026, 10, 21, 3, 30, tzinfo=IST))


# 4. indicators
class TestIndicators(unittest.TestCase):
    def test_rsi_known_values(self):
        up = pd.Series(np.arange(1, 40, dtype=float))
        self.assertAlmostEqual(ind.rsi(up).iloc[-1], 100.0)
        down = pd.Series(np.arange(40, 1, -1, dtype=float))
        self.assertLess(ind.rsi(down).iloc[-1], 1.0)

    def test_sma_atr_bollinger(self):
        s = pd.Series([1, 2, 3, 4, 5], dtype=float)
        self.assertEqual(ind.sma(s, 3).iloc[-1], 4.0)
        lo, mid, hi = ind.bollinger(s, 5, 2)
        self.assertAlmostEqual(mid.iloc[-1], 3.0)
        self.assertAlmostEqual(hi.iloc[-1] - mid.iloc[-1], 2 * np.std([1, 2, 3, 4, 5]))
        df = pd.DataFrame({"high": [10, 11, 12.0], "low": [9, 9.5, 10.0], "close": [9.5, 10.5, 11.0]})
        self.assertEqual(list(ind.true_range(df).round(2)), [1.0, 1.5, 2.0])

    def test_donchian_uses_prior_bars(self):
        df = synthetic_ohlcv(50, 2)
        lo, hi = ind.donchian(df, 10)
        self.assertAlmostEqual(hi.iloc[20], df["high"].iloc[10:20].max())

    def test_vwap_resets_daily(self):
        df = synthetic_intraday(2, 3)
        vw = ind.session_vwap(df)
        first_bar_day2 = df.index[375]
        tp = (df.loc[first_bar_day2, ["high", "low", "close"]]).mean()
        self.assertAlmostEqual(vw.loc[first_bar_day2], tp)

    def test_causality(self):
        """Changing a future bar must not change indicator values at earlier bars."""
        df = synthetic_ohlcv(300, 4)
        df2 = df.copy()
        df2.iloc[-1, df2.columns.get_loc("close")] *= 1.5
        for f in (lambda d: ind.rsi(d["close"]), lambda d: ind.atr(d), lambda d: ind.adx(d),
                  lambda d: ind.zscore(d["close"]), lambda d: ind.donchian(d)[1]):
            a, b = f(df).iloc[:-1], f(df2).iloc[:-1]
            pd.testing.assert_series_equal(a, b)


# 5. strategy signals
class TestStrategies(unittest.TestCase):
    def test_all_strategies_generate(self):
        daily = synthetic_ohlcv(600, 5)
        intra = synthetic_intraday(5, 5)
        bench = synthetic_ohlcv(600, 6)
        for s in REGISTRY.values():
            df = intra if s.style == "intraday" else daily
            sig = s.generate(df, None, {"benchmark": bench})
            self.assertEqual(list(sig.columns), ["entry", "exit", "stop", "target", "why"])
            self.assertEqual(len(sig), len(df))
            e = sig[sig["entry"]]
            if len(e):
                self.assertTrue((e["stop"] < df.loc[e.index, "close"]).all(), s.name)
                self.assertTrue((e["why"].str.len() > 0).all(), s.name)

    def test_sma_cross_exact(self):
        c = pd.Series([10] * 30 + list(range(11, 40)), dtype=float)
        idx = pd.date_range("2024-01-01", periods=len(c), freq="B", tz=IST)
        c.index = idx
        df = pd.DataFrame({"open": c, "high": c + 1, "low": c - 1, "close": c, "volume": 1000.0}, index=idx)
        sig = REGISTRY["sma_crossover"].generate(df, {"fast": 3, "slow": 10})
        self.assertEqual(int(sig["entry"].sum()), 1)
        self.assertEqual(sig.index[sig["entry"]][0], idx[30])   # first bar where SMA3 > SMA10

    def test_relative_strength_needs_benchmark(self):
        sig = REGISTRY["relative_strength"].generate(synthetic_ohlcv(300, 1), None, {})
        self.assertFalse(sig["entry"].any())

    def test_intraday_entries_respect_cutoff(self):
        df = synthetic_intraday(10, 7)
        for name in ("orb", "vwap_reversion", "prev_day_breakout"):
            sig = REGISTRY[name].generate(df)
            times = [t.time() for t in sig.index[sig["entry"]]]
            self.assertTrue(all(t <= dtime(14, 45) for t in times), name)


# 6. backtesting
class TestBacktest(unittest.TestCase):
    def _df(self, closes, opens=None, lows=None):
        c = pd.Series(closes, dtype=float)
        o = pd.Series(opens if opens is not None else closes, dtype=float)
        lo = pd.Series(lows if lows is not None else np.minimum(c, o) - 0.5, dtype=float)
        idx = pd.date_range("2024-01-01", periods=len(c), freq="B", tz=IST)
        return pd.DataFrame({"open": o.values, "high": np.maximum(c, o).values + 0.5, "low": lo.values,
                             "close": c.values, "volume": 1e5}, index=idx)

    class _OneShot:
        """Test strategy: enter on bar 1 with stop 90, exit signal on bar `exit_at`."""
        name, family, style, params, timeframe = "oneshot", "trend", "swing", {}, "1d"

        def __init__(self, exit_at=4, stop=90.0):
            self.exit_at, self.stopv = exit_at, stop

        def generate(self, df, params=None, context=None):
            s = pd.DataFrame({"entry": False, "exit": False, "stop": self.stopv, "target": np.nan, "why": "t"},
                             index=df.index)
            s.iloc[1, 0] = True
            s.iloc[self.exit_at, 1] = True
            return s

    def test_next_open_fill_and_costs(self):
        df = self._df([100, 100, 100, 104, 106, 106, 106], opens=[100, 100, 101, 104, 106, 107, 106])
        cfg = BTConfig(capital=100000, risk_per_trade_pct=0.01, slippage_bps=0, max_cost_to_risk_ratio=None,
                       min_reward_cost_ratio=None)
        r = run_backtest(df, self._OneShot(4), cfg=cfg)
        t = r.trades.iloc[0]
        self.assertEqual(t["entry_ts"], df.index[2])      # signal bar 1 -> fill bar 2 open
        self.assertEqual(t["entry"], 101.0)
        self.assertEqual(t["exit"], 107.0)                # exit signal bar 4 -> bar 5 open
        qty = int(min(100000 * 0.01 / (101 - 90), 100000 * 0.8 / 101))
        self.assertEqual(t["qty"], qty)
        exp_costs = CostModel().round_trip("EQ_DELIVERY", 101, 107, qty).total
        self.assertAlmostEqual(t["costs"], exp_costs, places=6)
        self.assertAlmostEqual(t["net_pnl"], 6 * qty - exp_costs, places=6)
        self.assertAlmostEqual(r.equity.iloc[-1], 100000 + t["net_pnl"], places=4)

    def test_gap_through_stop_fills_at_open(self):
        df = self._df([100, 100, 100, 80, 80], opens=[100, 100, 100, 85, 80], lows=[99, 99, 99, 79, 79])
        cfg = BTConfig(capital=100000, slippage_bps=0, max_cost_to_risk_ratio=None, min_reward_cost_ratio=None)
        r = run_backtest(df, self._OneShot(4, stop=95), cfg=cfg)
        t = r.trades.iloc[0]
        self.assertEqual(t["exit_reason"], "stop_gap")
        self.assertEqual(t["exit"], 85.0)                 # worse than the 95 stop: gap risk modelled

    def test_unaffordable_skipped(self):
        df = self._df([5000] * 10)
        r = run_backtest(df, self._OneShot(6, stop=4900), cfg=BTConfig(capital=1000))
        self.assertEqual(r.metrics["trades"], 0)
        self.assertGreaterEqual(r.skipped_unaffordable, 1)

    def test_small_account_delivery_costs_block(self):
        """At ₹1,000 a delivery round trip (~₹70 incl. DP) dwarfs a 2% risk budget: the cost filter blocks it."""
        df = self._df([100] * 10)
        r = run_backtest(df, self._OneShot(6, stop=95), cfg=BTConfig(capital=1000))
        self.assertEqual(r.metrics["trades"], 0)
        self.assertEqual(r.skipped_costs, 1)

    def test_intraday_squareoff(self):
        df = synthetic_intraday(3, 11)

        class S(self._OneShot):
            style = "intraday"

            def generate(s, d, params=None, context=None):
                g = pd.DataFrame({"entry": False, "exit": False, "stop": d["close"] * 0.5, "target": np.nan,
                                  "why": "t"}, index=d.index)
                g.iloc[20, 0] = True
                return g
        r = run_backtest(df, S(), cfg=BTConfig(capital=100000, max_cost_to_risk_ratio=None, min_reward_cost_ratio=None))
        t = r.trades.iloc[0]
        self.assertEqual(t["exit_reason"], "squareoff")
        self.assertEqual(t["exit_ts"].date(), t["entry_ts"].date())
        self.assertLessEqual(t["exit_ts"].time(), dtime(15, 10))

    def test_chrono_split(self):
        df = synthetic_ohlcv(100)
        a, b, c = chrono_split(df)
        self.assertTrue(a.index.max() < b.index.min() < c.index.min())


# 7. transaction costs
class TestCosts(unittest.TestCase):
    def test_intraday_equity(self):
        c = CostModel().order_cost("EQ_INTRADAY", "SELL", 500, 2)  # ₹1,000 turnover
        self.assertAlmostEqual(c.brokerage, 1.0)                  # min(20, 0.1%)
        self.assertAlmostEqual(c.stt, 0.25)                       # 0.025% sell
        self.assertAlmostEqual(c.stamp, 0.0)                      # buy side only
        self.assertAlmostEqual(c.gst, (c.brokerage + c.exchange + c.sebi) * 0.18)

    def test_delivery_has_dp_on_sell(self):
        cm = CostModel()
        s = cm.order_cost("EQ_DELIVERY", "SELL", 100, 5)
        self.assertAlmostEqual(s.dp, 23.6)
        self.assertAlmostEqual(s.stt, 0.5)
        b = cm.order_cost("EQ_DELIVERY", "BUY", 100, 5)
        self.assertAlmostEqual(b.stamp, 500 * 0.00015)

    def test_fo_2026_stt(self):
        cm = CostModel()
        self.assertAlmostEqual(cm.order_cost("FUT", "SELL", 1000, 100).stt, 100000 * 0.0005)
        self.assertAlmostEqual(cm.order_cost("OPT", "SELL", 10, 75).stt, 750 * 0.0015)
        self.assertEqual(cm.order_cost("OPT", "BUY", 10, 75).brokerage, 20.0)


# 8/9. position sizing, capital & margin rejection, stale data
class TestRisk(unittest.TestCase):
    def setUp(self):
        self.L = RiskLimits()
        self.re = RiskEngine(self.L)
        self.re.time_fn = lambda: dtime(11, 0)
        self.ins = eq_instrument()
        self.acct = AccountSnapshot(available_cash=1000.0, segments_enabled=("NSE", "BSE"), products_enabled=("I", "D"))

    def intent(self, entry=400, stop=395, target=420, product="I", age=5):
        return OrderIntent(self.ins.instrument_key, "BUY", entry, stop, target, product, "t", "sig1", time.time() - age)

    def test_sizing_by_risk(self):
        d = self.re.check(self.intent(stop=390), self.ins, quote(), self.acct)
        self.assertTrue(d.approved, d.reasons)
        # risk cap: 1000*2% / (400.9 - 390) = 1.83 -> 1 share; exposure cap 800/400.9 -> 1
        self.assertEqual(d.quantity, 1)
        self.assertAlmostEqual(d.limit_price, round_to_tick(400.1 * 1.002, 0.05, "up"))

    def test_unaffordable_rejected_not_resized(self):
        d = self.re.check(self.intent(entry=1500, stop=1480), self.ins, quote(ltp=1500, bid=1499.9, ask=1500.1),
                          self.acct)
        self.assertFalse(d.approved)
        self.assertTrue(any(r.startswith("affordability") for r in d.reasons))

    def test_delivery_costs_reject(self):
        d = self.re.check(self.intent(stop=390, target=410, product="D"), self.ins, quote(), self.acct)
        self.assertFalse(d.approved)
        self.assertTrue(any("costs" in r for r in d.reasons))

    def test_stale_quote_and_signal(self):
        d = self.re.check(self.intent(), self.ins, quote(age=120), self.acct)
        self.assertTrue(any(r.startswith("stale_quote") for r in d.reasons))
        d = self.re.check(self.intent(age=600), self.ins, quote(), self.acct)
        self.assertTrue(any(r.startswith("stale_signal") for r in d.reasons))

    def test_wide_spread(self):
        d = self.re.check(self.intent(), self.ins, quote(bid=396, ask=404), self.acct)
        self.assertTrue(any(r.startswith("spread") for r in d.reasons))

    def test_derivatives_and_option_writing_blocked(self):
        fo = eq_instrument("NSE_FO|1", "NIFTY")
        fo.segment, fo.option_type = "NSE_FO", "CE"
        i = self.intent()
        i.instrument_key = "NSE_FO|1"
        i.side = "SELL"
        d = self.re.check(i, fo, quote("NSE_FO|1"), self.acct)
        self.assertTrue(any(r.startswith("segment") for r in d.reasons))
        self.assertTrue(any(r.startswith("option_writing") for r in d.reasons))

    def test_entry_cutoff(self):
        self.re.time_fn = lambda: dtime(15, 0)
        d = self.re.check(self.intent(stop=390), self.ins, quote(), self.acct)
        self.assertTrue(any(r.startswith("entry_cutoff") for r in d.reasons))

    def test_portfolio_limits(self):
        acct = AccountSnapshot(available_cash=1000, positions=[
            {"instrument_key": "A", "quantity": 1, "value": 10}, {"instrument_key": "B", "quantity": 1, "value": 10}],
            orders_today=10)
        d = self.re.check(self.intent(stop=390), self.ins, quote(), acct)
        self.assertTrue(any(r.startswith("max_positions") for r in d.reasons))
        self.assertTrue(any(r.startswith("max_orders") for r in d.reasons))

    # 12. daily loss limit
    def test_daily_loss(self):
        acct = AccountSnapshot(available_cash=1000, realized_pnl_today=-40, unrealized_pnl_today=-15)
        self.assertTrue(self.re.daily_loss_breached(acct))
        d = self.re.check(self.intent(stop=390), self.ins, quote(), acct)
        self.assertTrue(any(r.startswith("daily_loss") for r in d.reasons))

    def test_exit_qty_cannot_exceed_position(self):
        acct = AccountSnapshot(available_cash=1000, positions=[{"instrument_key": self.ins.instrument_key,
                                                                "quantity": 2, "value": 800}])
        i = OrderIntent(self.ins.instrument_key, "SELL", 0, 0, None, "I", "x", "x1", time.time(), True, 3)
        self.assertFalse(self.re.check(i, self.ins, quote(), acct).approved)
        i.quantity = 2
        self.assertTrue(self.re.check(i, self.ins, quote(), acct).approved)


# 10/13/14/16/17. orders, state machine, kill switch
class TestExecution(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kill = Path(self.tmp.name) / "KILL"
        self.db = mem_db()
        self.state = ExecutionState(self.db, kill_file=self.kill)
        self.client = FakeClient()
        self.om = OrderManager(self.client, self.db, self.state)

    def tearDown(self):
        self.tmp.cleanup()

    def activate(self):
        self.state.mark_live_ready({"x": {"ok": True}})
        self.state.activate_live(CONFIRM_PHRASE)

    def req(self):
        return OrderRequest("NSE_EQ|INE154A01025", "BUY", 1, 401.0)

    def test_orders_blocked_unless_live_active(self):
        with self.assertRaises(PermissionError):
            self.om.submit(self.req(), "s1", "t")
        self.assertEqual(self.client.placed, [])

    def test_activation_requires_phrase_and_ready(self):
        with self.assertRaises(StateError):
            self.state.activate_live(CONFIRM_PHRASE)     # not LIVE_READY
        self.state.mark_live_ready({"x": {"ok": True}})
        with self.assertRaises(StateError):
            self.state.activate_live("yes")
        with self.assertRaises(StateError):
            self.state.mark_live_ready({"token": {"ok": False}})

    def test_restart_never_resumes_live(self):
        self.activate()
        self.assertEqual(self.state.state, "LIVE_ACTIVE")
        restarted = ExecutionState(self.db, kill_file=self.kill)
        self.assertEqual(restarted.state, "LIVE_READY")

    def test_activation_expires_next_day(self):
        self.activate()
        st = self.db.get_state("exec_state")
        st["activation_date"] = "2000-01-01"
        self.state._st = st
        ok, why = self.state.can_place_orders()
        self.assertFalse(ok)
        self.assertIn("expired", why)

    def test_duplicate_prevention(self):
        self.activate()
        r = self.om.submit(self.req(), "sigA", "t")
        self.assertEqual(r["status"], "SUBMITTED")
        with self.assertRaises(DuplicateOrder):
            self.om.submit(self.req(), "sigA", "t")
        self.assertEqual(len(self.client.placed), 1)

    def test_timeout_is_unknown_and_reconciled_not_retried(self):
        self.activate()
        self.client.mode = "timeout"
        r = self.om.submit(self.req(), "sigB", "t")
        self.assertEqual(r["status"], "UNKNOWN")
        with self.assertRaises(DuplicateOrder):           # cannot blindly resubmit
            self.om.submit(self.req(), "sigB", "t")
        tag = make_tag("IQ", "sigB", "E")
        self.client.history[tag] = [{"order_id": "X9", "status": "complete", "filled_quantity": 1, "average_price": 401}]
        out = self.om.reconcile_unknown()
        self.assertEqual(out[0]["status"], "FILLED")
        self.assertEqual(len(self.client.placed), 1)

    def test_rejection_recorded(self):
        self.activate()
        self.client.mode = "reject"
        r = self.om.submit(self.req(), "sigC", "t")
        self.assertEqual(r["status"], "REJECTED")
        self.assertIn("insufficient", r["status_message"])
        self.assertEqual(self.om.consecutive_failures, 1)

    def test_partial_fill_and_refresh(self):
        self.activate()
        r = self.om.submit(OrderRequest("NSE_EQ|INE154A01025", "BUY", 10, 401.0), "sigD", "t")
        self.client.book[0].update(status="open", filled_quantity=4)
        ch = self.om.refresh()
        self.assertEqual(ch[0]["status"], "PARTIAL")
        self.assertEqual(self.db.get_order(r["client_tag"])["filled_quantity"], 4)
        self.assertEqual(map_broker_status("cancelled", 4, 10), "PARTIAL_CANCELLED")
        self.assertEqual(map_broker_status("complete", 10, 10), "FILLED")

    def test_restart_recovery_from_db(self):
        self.activate()
        r = self.om.submit(self.req(), "sigE", "t")
        om2 = OrderManager(self.client, self.db, ExecutionState(self.db, kill_file=self.kill))
        self.assertEqual([o["client_tag"] for o in om2.active_orders()], [r["client_tag"]])

    def test_kill_file_halts(self):
        self.activate()
        self.kill.write_text("x")
        self.assertEqual(self.state.state, "HALTED")
        with self.assertRaises(PermissionError):
            self.om.submit(self.req(), "sigF", "t")
        with self.assertRaises(StateError):
            self.state.resume("checked")                   # KILL file still present
        self.kill.unlink()
        self.state.resume("checked")
        self.assertEqual(self.state.state, "LIVE_READY")   # never straight back to LIVE_ACTIVE

    def test_kill_switch_engine_cancels(self):
        from indiaquant.config import Settings
        from indiaquant.data.calendar import MarketCalendar
        from indiaquant.execution.engine import TradingEngine
        self.activate()
        self.om.submit(self.req(), "sigG", "t")
        eng = TradingEngine(Settings(), self.db, self.client, self.state, MarketCalendar(self.db))
        eng.om = self.om
        res = eng.kill_switch("test")
        self.assertTrue(res["halted"])
        self.assertEqual(res["cancel_requests"], 1)
        self.assertEqual(self.client.cancelled, ["OID1"])
        self.assertEqual(self.state.state, "HALTED")

    def test_position_reconciliation(self):
        issues = reconcile_positions({"A": 5}, [{"instrument_token": "A", "quantity": 3}])
        self.assertEqual(len(issues), 1)
        self.assertEqual(reconcile_positions({"A": 3}, [{"instrument_token": "A", "quantity": 3}]), [])


# 15. broker API error handling
class _Resp:
    def __init__(self, status, body):
        self.status_code, self._b, self.text = status, body, json.dumps(body)

    def json(self):
        return self._b


class _Sess:
    def __init__(self, responses):
        self.r, self.calls = list(responses), []

    def request(self, method, url, **kw):
        self.calls.append((method, url, kw))
        x = self.r.pop(0)
        if isinstance(x, Exception):
            raise x
        return x

    post = None


class TestBrokerErrors(unittest.TestCase):
    def client(self, responses):
        c = UpstoxClient("tok", session=_Sess(responses))
        c.std_rl = SlidingWindowLimiter([(1, 1000)])
        c.order_rl = SlidingWindowLimiter([(1, 1000)])
        return c

    def test_401_raises_auth_expired(self):
        c = self.client([_Resp(401, {"status": "error", "errors": [{"message": "Invalid token"}]})])
        with self.assertRaises(AuthExpired):
            c.profile()

    def test_get_retries_on_5xx(self):
        import indiaquant.broker.upstox as u
        orig = u.time.sleep
        u.time.sleep = lambda s: None
        try:
            c = self.client([_Resp(503, {}), _Resp(200, {"status": "success", "data": {"user_id": "X"}})])
            self.assertEqual(c.profile()["user_id"], "X")
        finally:
            u.time.sleep = orig

    def test_place_order_never_retried_on_timeout(self):
        import requests
        sess = _Sess([requests.Timeout("t")])
        c = self.client([])
        c.s = sess
        with self.assertRaises(OrderStatusUnknown):
            c.place_order(OrderRequest("NSE_EQ|X", "BUY", 1, 10.0, tag="T1"))
        self.assertEqual(len(sess.calls), 1)

    def test_market_orders_refused_client_side(self):
        c = self.client([])
        with self.assertRaises(OrderRejected):
            c.place_order(OrderRequest("NSE_EQ|X", "BUY", 1, 10.0, order_type="MARKET"))

    def test_order_payload_matches_v3_schema(self):
        sess = _Sess([_Resp(200, {"status": "success", "data": {"order_ids": ["1"]}})])
        c = self.client([])
        c.s = sess
        self.assertEqual(c.place_order(OrderRequest("NSE_EQ|X", "BUY", 2, 10.5, tag="T2")), ["1"])
        method, url, kw = sess.calls[0]
        self.assertEqual((method, url), ("POST", "https://api-hft.upstox.com/v3/order/place"))
        body = kw["json"]
        for f in ("quantity", "product", "validity", "price", "tag", "instrument_token", "order_type",
                  "transaction_type", "disclosed_quantity", "trigger_price", "is_amo", "slice"):
            self.assertIn(f, body)

    def test_candle_parsing(self):
        df = UpstoxClient.candles_to_df({"data": {"candles": [["2025-01-02T00:00:00+05:30", 1, 2, 0.5, 1.5, 100, 0],
                                                              ["2025-01-01T00:00:00+05:30", 1, 2, 0.5, 1.2, 90, 0]]}})
        self.assertTrue(df.index.is_monotonic_increasing)
        self.assertEqual(df["close"].iloc[-1], 1.5)

    def test_rate_limiter_blocks(self):
        t = [0.0]
        slept = []
        lim = SlidingWindowLimiter([(1.0, 2)], clock=lambda: t[0],
                                   sleeper=lambda s: (slept.append(s), t.__setitem__(0, t[0] + s)))
        for _ in range(3):
            lim.acquire()
        self.assertEqual(len(slept), 1)
        self.assertGreater(slept[0], 0.9)


# 18. credential redaction
class TestRedaction(unittest.TestCase):
    def test_redacts(self):
        os.environ["UPSTOX_CLIENT_SECRET"] = "supersecretvalue123"
        s = redact("Authorization: Bearer eyJabc.def-ghi and client_secret=supersecretvalue123 code=abc123 "
                   '{"access_token": "tok999"}')
        for leak in ("eyJabc", "supersecretvalue123", "abc123", "tok999"):
            self.assertNotIn(leak, s)
        rec = logging.LogRecord("x", 20, "f", 1, "token %s", ("Bearer abc.def",), None)
        RedactingFilter().filter(rec)
        self.assertNotIn("abc.def", rec.getMessage())
        del os.environ["UPSTOX_CLIENT_SECRET"]

    def test_secrets_repr(self):
        from indiaquant.config import Secrets
        self.assertNotIn("xyz", repr(Secrets("id1", "xyz", "http://127.0.0.1:8765/callback", "tok")))


# 19. database persistence
class TestDatabase(unittest.TestCase):
    def test_roundtrip_and_upsert(self):
        with tempfile.TemporaryDirectory() as d:
            p = str(Path(d) / "t.db")
            db = Database(p)
            df = synthetic_ohlcv(10)
            self.assertEqual(db.upsert_candles("K", "1d", df, "SYNTHETIC_TEST_DATA"), 10)
            db.upsert_candles("K", "1d", df.iloc[-2:], "SYNTHETIC_TEST_DATA")
            db.set_state("a", {"b": 1})
            db.conn.close()
            db2 = Database(p)
            back = db2.load_candles("K", "1d")
            self.assertEqual(len(back), 10)
            self.assertAlmostEqual(back["close"].iloc[-1], df["close"].iloc[-1])
            self.assertEqual(db2.get_state("a"), {"b": 1})
            self.assertEqual(db2.last_candle_ts("K", "1d"), back.index[-1])
            db2.conn.close()


# misc analytics
class TestAnalytics(unittest.TestCase):
    def test_black_scholes_parity_and_iv(self):
        S, K, T, r = 100, 100, 0.25, 0.065
        c, p = bs_price(S, K, T, r, 0.2, "CE"), bs_price(S, K, T, r, 0.2, "PE")
        self.assertAlmostEqual(c - p, S - K * np.exp(-r * T), places=6)
        self.assertAlmostEqual(implied_vol(c, S, K, T, r, "CE"), 0.2, places=4)
        g = greeks(S, K, T, r, 0.2, "CE")
        self.assertTrue(g.estimate)
        self.assertTrue(0.5 < g.delta < 0.65)

    def test_cointegration(self):
        rng = np.random.default_rng(0)
        x = np.cumsum(rng.normal(0, 1, 800)) + 200
        y = 1.5 * x + rng.normal(0, 1, 800)
        idx = pd.date_range("2020-01-01", periods=800, freq="B")
        self.assertTrue(engle_granger(pd.Series(y, idx), pd.Series(x, idx))["cointegrated"])
        z = np.cumsum(rng.normal(0, 1, 800)) + 200
        self.assertFalse(engle_granger(pd.Series(z, idx), pd.Series(x, idx))["cointegrated"])

    def test_regime_and_shield_outputs(self):
        df = synthetic_ohlcv(400, 3)
        self.assertTrue(classify(df).labels)
        spike = df.copy()
        spike.iloc[-1, spike.columns.get_loc("volume")] *= 20
        spike.iloc[-1, spike.columns.get_loc("close")] *= 1.12
        spike.iloc[-1, spike.columns.get_loc("high")] = spike["close"].iloc[-1] * 1.01
        r = stockshield.analyze(spike)
        self.assertGreater(r.contributions["abnormal_volume"], 0)
        self.assertGreater(r.score, stockshield.analyze(df).score)
        self.assertTrue(r.limitations)

    def test_feed_dedupe_and_ordering(self):
        b = QuoteBook()
        now = time.time()
        self.assertTrue(b.update(Quote("K", 10, now, now)))
        self.assertFalse(b.update(Quote("K", 10, now, now)))          # duplicate
        self.assertFalse(b.update(Quote("K", 11, now - 5, now)))      # out of order
        self.assertTrue(b.update(Quote("K", 12, now + 1, now)))
        self.assertIsNone(b.get("K", max_age=10, now=now + 60))       # stale
        self.assertTrue(is_fresh(now - 5, 30, now))
        self.assertFalse(is_fresh(now - 50, 30, now))

    def test_settings_validation(self):
        s = Settings()
        self.assertEqual(validate_settings(s), [])
        s.risk.allow_option_writing = True
        s.dashboard_host = "0.0.0.0"
        errs = validate_settings(s)
        self.assertTrue(any("option_writing" in e for e in errs))
        self.assertTrue(any("dashboard_host" in e for e in errs))


if __name__ == "__main__":
    unittest.main()
