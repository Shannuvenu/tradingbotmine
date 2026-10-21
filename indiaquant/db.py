"""SQLite persistence with versioned migrations.

SQLite (WAL mode) runs immediately on Windows with no server. A PostgreSQL
migration path is documented in docs/DATABASE.md: the schema below uses only
portable types and every query goes through this module.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

MIGRATIONS: list[str] = [
    # v1
    """
    CREATE TABLE IF NOT EXISTS instruments (
        instrument_key TEXT PRIMARY KEY, exchange TEXT, segment TEXT, instrument_type TEXT,
        trading_symbol TEXT, name TEXT, isin TEXT, exchange_token TEXT, lot_size INTEGER,
        tick_size REAL, freeze_quantity REAL, expiry TEXT, strike REAL, option_type TEXT,
        underlying_key TEXT, underlying_symbol TEXT, weekly INTEGER, security_type TEXT,
        updated_at TEXT);
    CREATE INDEX IF NOT EXISTS ix_instr_symbol ON instruments(trading_symbol);
    CREATE INDEX IF NOT EXISTS ix_instr_underlying ON instruments(underlying_symbol, expiry);
    CREATE TABLE IF NOT EXISTS candles (
        instrument_key TEXT, interval TEXT, ts TEXT, open REAL, high REAL, low REAL, close REAL,
        volume REAL, oi REAL, source TEXT, PRIMARY KEY (instrument_key, interval, ts));
    CREATE TABLE IF NOT EXISTS orders (
        client_tag TEXT PRIMARY KEY, broker_order_id TEXT, instrument_key TEXT, side TEXT,
        quantity INTEGER, price REAL, trigger_price REAL, order_type TEXT, product TEXT,
        status TEXT, filled_quantity INTEGER DEFAULT 0, average_price REAL, strategy TEXT,
        signal_id TEXT, status_message TEXT, created_at TEXT, updated_at TEXT, raw TEXT);
    CREATE INDEX IF NOT EXISTS ix_orders_status ON orders(status);
    CREATE TABLE IF NOT EXISTS fills (
        trade_id TEXT PRIMARY KEY, broker_order_id TEXT, instrument_key TEXT, side TEXT,
        quantity INTEGER, price REAL, ts TEXT);
    CREATE TABLE IF NOT EXISTS signals (
        signal_id TEXT PRIMARY KEY, ts TEXT, instrument_key TEXT, strategy TEXT, side TEXT,
        entry REAL, stop REAL, target REAL, style TEXT, data_ts TEXT, explanation TEXT,
        decision TEXT, decision_reasons TEXT);
    CREATE TABLE IF NOT EXISTS kv_state (key TEXT PRIMARY KEY, value TEXT, updated_at TEXT);
    CREATE TABLE IF NOT EXISTS audit_log (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT,
        category TEXT, message TEXT, payload TEXT);
    CREATE TABLE IF NOT EXISTS api_errors (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT,
        endpoint TEXT, status INTEGER, message TEXT);
    CREATE TABLE IF NOT EXISTS backtest_runs (run_id TEXT PRIMARY KEY, ts TEXT, strategy TEXT,
        instrument_key TEXT, params TEXT, period TEXT, split TEXT, metrics TEXT, data_source TEXT,
        data_hash TEXT);
    CREATE TABLE IF NOT EXISTS holidays (date TEXT, exchange TEXT, description TEXT,
        holiday_type TEXT, PRIMARY KEY (date, exchange));
    CREATE TABLE IF NOT EXISTS news (id TEXT PRIMARY KEY, ts TEXT, fetched_at TEXT,
        instrument_key TEXT, headline TEXT, source TEXT, url TEXT);
    CREATE TABLE IF NOT EXISTS model_registry (model_id TEXT PRIMARY KEY, ts TEXT, task TEXT,
        features TEXT, params TEXT, data_hash TEXT, metrics TEXT, baseline_metrics TEXT,
        passed_validation INTEGER);
    CREATE TABLE IF NOT EXISTS data_quality (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT,
        instrument_key TEXT, interval TEXT, issue TEXT, detail TEXT);
    """,
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Database:
    def __init__(self, path: str):
        self.path = path
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.migrate()

    # ------------------------------------------------------------------ core
    @contextmanager
    def tx(self):
        with self._lock:
            self.conn.execute("BEGIN")
            try:
                yield self.conn
                self.conn.execute("COMMIT")
            except Exception:
                self.conn.execute("ROLLBACK")
                raise

    def execute(self, sql: str, params=()):
        with self._lock:
            return self.conn.execute(sql, params)

    def query(self, sql: str, params=()) -> list[dict]:
        with self._lock:
            return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def migrate(self) -> int:
        with self._lock:
            self.conn.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER)")
            row = self.conn.execute("SELECT MAX(version) v FROM schema_version").fetchone()
            current = row["v"] or 0
            for i, sql in enumerate(MIGRATIONS, start=1):
                if i > current:
                    self.conn.executescript(sql)
                    self.conn.execute("INSERT INTO schema_version VALUES (?)", (i,))
            return len(MIGRATIONS)

    # ----------------------------------------------------------- kv / audit
    def set_state(self, key: str, value) -> None:
        self.execute("INSERT INTO kv_state(key,value,updated_at) VALUES(?,?,?) "
                     "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                     (key, json.dumps(value), _now()))

    def get_state(self, key: str, default=None):
        r = self.query("SELECT value FROM kv_state WHERE key=?", (key,))
        return json.loads(r[0]["value"]) if r else default

    def audit(self, category: str, message: str, payload: dict | None = None) -> None:
        from .logging_setup import redact
        self.execute("INSERT INTO audit_log(ts,category,message,payload) VALUES(?,?,?,?)",
                     (_now(), category, redact(message), redact(json.dumps(payload or {}, default=str))))

    def api_error(self, endpoint: str, status: int, message: str) -> None:
        from .logging_setup import redact
        self.execute("INSERT INTO api_errors(ts,endpoint,status,message) VALUES(?,?,?,?)",
                     (_now(), endpoint, status, redact(message)[:2000]))

    # -------------------------------------------------------------- candles
    def upsert_candles(self, instrument_key: str, interval: str, df: pd.DataFrame, source: str) -> int:
        if df is None or df.empty:
            return 0
        rows = [(instrument_key, interval, pd.Timestamp(ts).isoformat(), float(r.open), float(r.high),
                 float(r.low), float(r.close), float(r.volume), float(getattr(r, "oi", 0) or 0), source)
                for ts, r in df.iterrows()]
        with self.tx() as c:
            c.executemany("INSERT INTO candles VALUES (?,?,?,?,?,?,?,?,?,?) ON CONFLICT(instrument_key,"
                          "interval,ts) DO UPDATE SET open=excluded.open, high=excluded.high, low=excluded.low,"
                          " close=excluded.close, volume=excluded.volume, oi=excluded.oi, source=excluded.source",
                          rows)
        return len(rows)

    def load_candles(self, instrument_key: str, interval: str, start: str | None = None,
                     end: str | None = None) -> pd.DataFrame:
        sql = "SELECT ts,open,high,low,close,volume,oi,source FROM candles WHERE instrument_key=? AND interval=?"
        p: list = [instrument_key, interval]
        if start:
            sql += " AND ts>=?"
            p.append(start)
        if end:
            sql += " AND ts<=?"
            p.append(end)
        sql += " ORDER BY ts"
        rows = self.query(sql, p)
        if not rows:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume", "oi", "source"])
        df = pd.DataFrame(rows)
        df["ts"] = pd.to_datetime(df["ts"], format="ISO8601")
        return df.set_index("ts")

    def last_candle_ts(self, instrument_key: str, interval: str):
        r = self.query("SELECT MAX(ts) t FROM candles WHERE instrument_key=? AND interval=?",
                       (instrument_key, interval))
        return pd.Timestamp(r[0]["t"]) if r and r[0]["t"] else None

    # --------------------------------------------------------------- orders
    def save_order(self, o: dict) -> None:
        o = dict(o)
        o.setdefault("created_at", _now())
        o["updated_at"] = _now()
        cols = ["client_tag", "broker_order_id", "instrument_key", "side", "quantity", "price", "trigger_price",
                "order_type", "product", "status", "filled_quantity", "average_price", "strategy", "signal_id",
                "status_message", "created_at", "updated_at", "raw"]
        vals = [o.get(c) if c != "raw" else json.dumps(o.get("raw") or {}, default=str) for c in cols]
        upd = ", ".join(f"{c}=excluded.{c}" for c in cols if c not in ("client_tag", "created_at"))
        self.execute(f"INSERT INTO orders({','.join(cols)}) VALUES ({','.join('?'*len(cols))}) "
                     f"ON CONFLICT(client_tag) DO UPDATE SET {upd}", vals)

    def get_order(self, client_tag: str) -> dict | None:
        r = self.query("SELECT * FROM orders WHERE client_tag=?", (client_tag,))
        return r[0] if r else None

    def orders(self, statuses: tuple[str, ...] | None = None, since: str | None = None) -> list[dict]:
        sql, p = "SELECT * FROM orders WHERE 1=1", []
        if statuses:
            sql += f" AND status IN ({','.join('?'*len(statuses))})"
            p += list(statuses)
        if since:
            sql += " AND created_at>=?"
            p.append(since)
        return self.query(sql + " ORDER BY created_at", p)

    def save_signal(self, s: dict) -> None:
        cols = ["signal_id", "ts", "instrument_key", "strategy", "side", "entry", "stop", "target", "style",
                "data_ts", "explanation", "decision", "decision_reasons"]
        self.execute(f"INSERT OR REPLACE INTO signals({','.join(cols)}) VALUES ({','.join('?'*len(cols))})",
                     [s.get(c) if not isinstance(s.get(c), (list, dict)) else json.dumps(s.get(c)) for c in cols])

    def save_backtest(self, run: dict) -> None:
        cols = ["run_id", "ts", "strategy", "instrument_key", "params", "period", "split", "metrics",
                "data_source", "data_hash"]
        self.execute(f"INSERT OR REPLACE INTO backtest_runs VALUES ({','.join('?'*len(cols))})",
                     [run.get(c) if isinstance(run.get(c), (str, type(None))) else json.dumps(run.get(c), default=str)
                      for c in cols])

    def log_quality(self, instrument_key: str, interval: str, issue: str, detail: str) -> None:
        self.execute("INSERT INTO data_quality(ts,instrument_key,interval,issue,detail) VALUES(?,?,?,?,?)",
                     (_now(), instrument_key, interval, issue, detail))
