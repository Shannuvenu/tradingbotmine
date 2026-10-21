"""Indian market sessions, IST handling and holiday checks.

IST is UTC+05:30 with no DST, so a fixed offset is exact and avoids needing
the tzdata package on Windows.

Normal equity session (NSE & BSE): 09:15–15:30 IST, pre-open 09:00–09:15.
Holidays are NOT hardcoded: they are loaded from Upstox's Market Holidays API
(GET /v2/market/holidays) into the `holidays` table. If holidays for the
current year are missing, `is_trading_day` returns None (unknown) and the live
engine refuses to trade until they are loaded or the exchange-status API
confirms the market is open.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30), name="IST")

PRE_OPEN_START = time(9, 0)
MARKET_OPEN = time(9, 15)
MARKET_CLOSE = time(15, 30)


def now_ist() -> datetime:
    return datetime.now(IST)


def to_ist(ts) -> datetime:
    """Convert datetime / pandas Timestamp / ISO string to aware IST datetime.
    Naive values are assumed to already be IST (Upstox candles carry +05:30)."""
    import pandas as pd
    t = pd.Timestamp(ts)
    if t.tzinfo is None:
        return t.to_pydatetime().replace(tzinfo=IST)
    return t.tz_convert(IST).to_pydatetime()


@dataclass
class SessionStatus:
    phase: str          # CLOSED_HOLIDAY | CLOSED_WEEKEND | PRE_OPEN | OPEN | CLOSED | UNKNOWN_HOLIDAY_DATA
    is_open: bool
    detail: str


class MarketCalendar:
    def __init__(self, db=None):
        self.db = db

    def _holiday(self, d: date, exchange: str):
        if self.db is None:
            return None
        rows = self.db.query("SELECT * FROM holidays WHERE date=? AND exchange IN (?, 'ALL')",
                             (d.isoformat(), exchange))
        return rows[0] if rows else False

    def has_holiday_data(self, year: int) -> bool:
        if self.db is None:
            return False
        r = self.db.query("SELECT COUNT(*) n FROM holidays WHERE date LIKE ?", (f"{year}-%",))
        return bool(r and r[0]["n"] > 0)

    def is_trading_day(self, d: date, exchange: str = "NSE"):
        if d.weekday() >= 5:
            return False
        h = self._holiday(d, exchange)
        if h:
            return False
        if not self.has_holiday_data(d.year):
            return None  # unknown
        return True

    def status(self, at: datetime | None = None, exchange: str = "NSE") -> SessionStatus:
        at = to_ist(at) if at is not None else now_ist()
        d = at.date()
        if d.weekday() >= 5:
            return SessionStatus("CLOSED_WEEKEND", False, "Weekend")
        td = self.is_trading_day(d, exchange)
        if td is False:
            return SessionStatus("CLOSED_HOLIDAY", False, "Exchange holiday")
        t = at.time()
        if td is None:
            if PRE_OPEN_START <= t < MARKET_CLOSE:
                return SessionStatus("UNKNOWN_HOLIDAY_DATA", False,
                                     "Holiday list not loaded; run `python -m indiaquant.cli sync-holidays`")
            return SessionStatus("CLOSED", False, "Outside trading hours (holiday list not loaded)")
        if PRE_OPEN_START <= t < MARKET_OPEN:
            return SessionStatus("PRE_OPEN", False, "Pre-open call auction")
        if MARKET_OPEN <= t < MARKET_CLOSE:
            return SessionStatus("OPEN", True, "Normal market")
        return SessionStatus("CLOSED", False, "Outside trading hours")

    def store_holidays(self, payload: list[dict]) -> int:
        """Store Upstox holiday payload. A holiday applies to an exchange if it
        is listed in closed_exchanges. Trading-holiday rows store the exchange."""
        n = 0
        for h in payload:
            if h.get("holiday_type") != "TRADING_HOLIDAY":
                continue
            for ex in h.get("closed_exchanges", []) or []:
                self.db.execute("INSERT OR REPLACE INTO holidays VALUES (?,?,?,?)",
                                (h["date"], ex, h.get("description", ""), h.get("holiday_type")))
                n += 1
        # mark the year as loaded even if a year had zero holidays for NSE
        if payload:
            y = payload[0]["date"][:4]
            self.db.execute("INSERT OR REPLACE INTO holidays VALUES (?,?,?,?)",
                            (f"{y}-00-00", "_LOADED", "marker", "MARKER"))
        return n


def minutes_since_open(ts) -> float:
    t = to_ist(ts)
    o = t.replace(hour=9, minute=15, second=0, microsecond=0)
    return (t - o).total_seconds() / 60.0


def parse_hhmm(s: str) -> time:
    h, m = s.split(":")
    return time(int(h), int(m))
