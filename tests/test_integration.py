"""Integration tests: engine cycle in analysis mode, research pipeline (synthetic), dashboard script execution
against a stub Streamlit (records calls; no browser). All data SYNTHETIC TEST DATA."""
import importlib
import json
import sys
import tempfile
import types
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

import pandas as pd

from indiaquant.config import Settings
from indiaquant.data.calendar import IST, MarketCalendar
from indiaquant.data.validation import synthetic_ohlcv
from indiaquant.db import Database
from indiaquant.execution.engine import TradingEngine, approved_strategies
from indiaquant.execution.state import ExecutionState
from tests.fakes import FakeClient


class TestEngineCycle(unittest.TestCase):
    def test_analysis_mode_never_orders_and_research_gate(self):
        db = Database(":memory:")
        s = Settings()
        s.watchlist = ["NSE_EQ|INE154A01025"]
        s.enabled_strategies = ["sma_crossover", "rsi_reversion", "donchian_breakout", "bollinger_reversion"]
        db.upsert_candles(s.watchlist[0], "1d", synthetic_ohlcv(400, 3), "SYNTHETIC_TEST_DATA")
        state = ExecutionState(db, kill_file=Path(tempfile.gettempdir()) / "iq_no_kill_file")
        state.to_analysis()
        cal = MarketCalendar(db)
        cal.store_holidays([{"date": "2026-01-26", "holiday_type": "TRADING_HOLIDAY", "closed_exchanges": ["NSE"]}])
        client = FakeClient()
        eng = TradingEngine(s, db, client, state, cal)
        # force: session open, and a signal on the last bar of every strategy
        with mock.patch.object(cal, "status", return_value=types.SimpleNamespace(is_open=True, phase="OPEN")):
            from indiaquant.strategies import catalog
            orig = catalog.Strategy.latest_signal

            def always(self, df, key, params=None, context=None):
                from indiaquant.strategies.base import StrategySignal
                return StrategySignal(self.name, key, "BUY", float(df.close.iloc[-1]), float(df.close.iloc[-1]) * 0.98,
                                      None, self.style, str(df.index[-1]), "forced test signal", self.family)
            with mock.patch.object(catalog.Strategy, "latest_signal", always):
                info = eng.cycle()
        self.assertEqual(client.placed, [])                    # no orders in ANALYSIS
        self.assertTrue(info["decisions"])
        self.assertTrue(all(d["decision"] == "NO_TRADE" for d in info["decisions"]))  # research gate (synthetic only)
        sig = db.query("SELECT decision_reasons FROM signals LIMIT 1")[0]["decision_reasons"]
        self.assertIn("research gate", sig)

    def test_approved_strategies_ignores_synthetic(self):
        db = Database(":memory:")
        for src in ("SYNTHETIC_TEST_DATA", "upstox_v3_historical"):
            db.save_backtest({"run_id": src, "ts": "2026-10-21T00:00:00", "strategy": "orb", "instrument_key": "K",
                              "params": "{}", "period": "{}", "split": "{}", "metrics": json.dumps({"verdict": "CANDIDATE"}),
                              "data_source": src, "data_hash": "x"})
        self.assertEqual(approved_strategies(db, "K"), {"orb"})
        db2 = Database(":memory:")
        db2.save_backtest({"run_id": "a", "ts": "t", "strategy": "orb", "instrument_key": "K", "params": "{}",
                           "period": "{}", "split": "{}", "metrics": json.dumps({"verdict": "CANDIDATE"}),
                           "data_source": "SYNTHETIC_TEST_DATA", "data_hash": "x"})
        self.assertEqual(approved_strategies(db2, "K"), set())


class TestResearch(unittest.TestCase):
    def test_synthetic_research_is_labelled_and_never_candidate(self):
        from indiaquant import research
        with tempfile.TemporaryDirectory() as d, mock.patch.object(research, "REPORT_DIR", Path(d)):
            db = Database(":memory:")
            s = Settings()
            res = research.run_research(db, s, synthetic=True, keys=s.watchlist[:3],
                                        strategies=["sma_crossover", "orb"])
            self.assertTrue(Path(res["report_path"]).exists())
            txt = Path(res["report_path"]).read_text(encoding="utf-8")
            self.assertIn("SYNTHETIC TEST DATA", txt)
            self.assertFalse((res["summary"]["verdict"] == "CANDIDATE").any())
            self.assertIn("cross_sectional_momentum", res["extras"])


class _Ctx:
    stub = None

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return getattr(_Ctx.stub, name)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _Stub(types.ModuleType):
    """Minimal Streamlit stand-in: every widget returns a sensible default; layout objects are context managers."""

    def __init__(self):
        super().__init__("streamlit")
        self.calls = []

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)

        def f(*a, **k):
            self.calls.append(name)
            if name in ("tabs", "columns"):
                n = a[0] if isinstance(a[0], int) else len(a[0])
                return [_Ctx() for _ in range(n)]
            if name in ("expander", "container", "spinner"):
                return _Ctx()
            if name == "cache_resource":
                return a[0] if a and callable(a[0]) else (lambda fn: fn)
            if name == "selectbox":
                opts = list(a[1]) if len(a) > 1 else []
                return opts[0] if opts else None
            if name == "text_input":
                return a[1] if len(a) > 1 else ""
            if name == "number_input":
                return k.get("value", 1)
            if name in ("button", "checkbox"):
                return False
            return None
        return f


class TestDashboard(unittest.TestCase):
    def test_dashboard_script_runs(self):  # noqa: C901
        st = _Stub()
        _Ctx.stub = st
        go = types.ModuleType("plotly.graph_objects")
        go.Figure = lambda *a, **k: types.SimpleNamespace(add_trace=lambda *x, **y: None,
                                                          update_layout=lambda *x, **y: None)
        go.Candlestick = go.Scatter = lambda *a, **k: None
        plotly = types.ModuleType("plotly")
        plotly.graph_objects = go
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
            from indiaquant import app as appmod
            from indiaquant.config import load_settings
            s = load_settings()
            s.db_path = str(Path(d) / "dash.db")
            db = Database(s.db_path)
            for i, k in enumerate(s.watchlist[:2] + [s.benchmark_key]):
                db.upsert_candles(k, "1d", synthetic_ohlcv(300, i), "SYNTHETIC_TEST_DATA")
            svc = appmod.Services(s, db, FakeClientNoToken(), ExecutionState(db, kill_file=Path(d) / "KILL"),
                                  MarketCalendar(db), None)
            saved = {k: sys.modules.get(k) for k in ("streamlit", "plotly", "plotly.graph_objects")}
            sys.modules.update({"streamlit": st, "plotly": plotly, "plotly.graph_objects": go})
            try:
                with mock.patch.object(appmod, "build", return_value=svc):
                    sys.modules.pop("dashboard.app", None)
                    importlib.import_module("dashboard.app")
            finally:
                for k, v in saved.items():
                    if v is None:
                        sys.modules.pop(k, None)
                    else:
                        sys.modules[k] = v
                sys.modules.pop("dashboard.app", None)
                db.conn.close()          # Windows cannot delete an open SQLite file
        for needed in ("tabs", "dataframe", "metric", "json", "button"):
            self.assertIn(needed, st.calls)


class FakeClientNoToken(FakeClient):
    @property
    def has_token(self):
        return False


if __name__ == "__main__":
    unittest.main()


class TestLoginAndHistory(unittest.TestCase):
    def test_oauth_callback_flow(self):
        """Simulates the browser redirect to the local callback; token exchange is mocked (no network)."""
        import threading
        import time as _t
        import urllib.request
        from urllib.parse import parse_qs, urlparse
        from indiaquant.broker import auth
        from indiaquant.config import Secrets
        with tempfile.TemporaryDirectory() as d:
            tok_file = Path(d) / "token.json"
            sec = Secrets("cid", "csecret", "http://127.0.0.1:8799/callback", "")
            captured = {}

            def fake_open(url):
                captured["url"] = url
                state = parse_qs(urlparse(url).query)["state"][0]

                def hit():
                    _t.sleep(0.3)
                    urllib.request.urlopen(f"http://127.0.0.1:8799/callback?code=CODE1&state={state}", timeout=5)
                threading.Thread(target=hit, daemon=True).start()
                return True

            with mock.patch.object(auth.Secrets, "from_env", return_value=sec), \
                    mock.patch.object(auth.webbrowser, "open", fake_open), \
                    mock.patch.object(auth, "TOKEN_FILE", tok_file), \
                    mock.patch.object(auth.UpstoxClient, "exchange_code",
                                      return_value={"access_token": "AT", "user_id": "U1", "exchanges": ["NSE"]}) as ex, \
                    mock.patch.object(auth, "save_token", lambda t, p: _real_save(t, p, tok_file)):
                rec = auth.interactive_login(open_browser=True, timeout_s=10)
            self.assertIn("response_type=code", captured["url"])
            self.assertIn("client_id=cid", captured["url"])
            ex.assert_called_once_with("CODE1", "cid", "csecret", "http://127.0.0.1:8799/callback")
            self.assertEqual(rec["user_id"], "U1")
            self.assertTrue(tok_file.exists())

    def test_history_incremental_chunks(self):
        from datetime import date
        from indiaquant.data.history import HistoryService, chunk_ranges
        self.assertEqual(len(chunk_ranges(date(2024, 1, 1), date(2024, 3, 31), 28)), 4)
        calls = []

        class C:
            def historical(self, key, unit, interval, to, frm):
                calls.append((unit, interval, frm, to))
                df = synthetic_ohlcv(5, start=frm)
                return df

        db = Database(":memory:")
        hs = HistoryService(C(), db)
        n = hs.update("K", "1m", start=date(2024, 1, 1), end=date(2024, 2, 15))
        self.assertEqual(len(calls), 2)
        self.assertGreater(n, 0)
        calls.clear()
        hs.update("K", "1m", end=date(2024, 2, 20))            # incremental: resumes from last stored day
        self.assertGreaterEqual(calls[0][2], "2024-01-29")



from indiaquant.broker.auth import save_token as _real_save  # noqa: E402
