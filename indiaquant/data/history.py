"""Incremental historical-candle download from Upstox Historical Candle Data V3.

Docs (verified 2026-10-21): GET /v3/historical-candle/{key}/{unit}/{interval}/{to}/{from}
  minutes 1..300: from Jan 2022; max 1 month per request for <=15m, 1 quarter for >15m
  hours 1..5: from Jan 2022, max 1 quarter
  days: from Jan 2000, max 1 decade; weeks/months: no limit
Candle row: [timestamp, open, high, low, close, volume, open_interest]

Corporate actions: Upstox does not document whether candles are split/bonus
adjusted. Validation flags >25% overnight jumps so a researcher can inspect them;
the corporate-actions API (Fundamentals) can be used to confirm.
"""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from ..logging_setup import get_logger
from .validation import clean_candles, validate_candles

log = get_logger("history")

INTERVALS = {  # our label -> (unit, interval, chunk_days, earliest)
    "1m": ("minutes", 1, 28, date(2022, 1, 1)),
    "3m": ("minutes", 3, 28, date(2022, 1, 1)),
    "5m": ("minutes", 5, 28, date(2022, 1, 1)),
    "15m": ("minutes", 15, 28, date(2022, 1, 1)),
    "30m": ("minutes", 30, 85, date(2022, 1, 1)),
    "1h": ("hours", 1, 85, date(2022, 1, 1)),
    "1d": ("days", 1, 3600, date(2000, 1, 1)),
    "1w": ("weeks", 1, 20000, date(2000, 1, 1)),
}


def chunk_ranges(start: date, end: date, chunk_days: int) -> list[tuple[date, date]]:
    out = []
    cur = start
    while cur <= end:
        nxt = min(cur + timedelta(days=chunk_days - 1), end)
        out.append((cur, nxt))
        cur = nxt + timedelta(days=1)
    return out


class HistoryService:
    def __init__(self, client, db):
        self.client, self.db = client, db

    def update(self, key: str, interval: str = "1d", start: date | None = None, end: date | None = None) -> int:
        unit, step, chunk, earliest = INTERVALS[interval]
        end = end or date.today()
        last = self.db.last_candle_ts(key, interval)
        if last is not None:
            # re-fetch the last stored bar's day to repair a partially-formed final candle
            start = max(last.date(), earliest)
        else:
            start = max(start or (end - timedelta(days=365 * 5 if interval == "1d" else 60)), earliest)
        total = 0
        for a, b in chunk_ranges(start, end, chunk):
            df = self.client.historical(key, unit, step, b.isoformat(), a.isoformat())
            if df.empty:
                continue
            rep = validate_candles(df, interval)
            for kind, detail in rep.issues:
                self.db.log_quality(key, interval, kind, detail)
            df = clean_candles(df)
            total += self.db.upsert_candles(key, interval, df, source="upstox_v3_historical")
        log.info("history %s %s: %d rows upserted", key, interval, total)
        return total

    def load(self, key: str, interval: str = "1d", start: str | None = None) -> pd.DataFrame:
        return self.db.load_candles(key, interval, start)
