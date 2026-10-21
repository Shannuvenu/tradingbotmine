"""Normalized instrument master built from Upstox BOD instrument JSON files.

Source: https://upstox.com/developer/api-documentation/instruments
  https://assets.upstox.com/market-quote/instruments/exchange/{NSE,BSE,complete}.json.gz
Files refresh daily around 06:00 IST and exclude expired contracts.

Key facts encoded here (from the official docs, Oct 2026):
* `instrument_key` (e.g. "NSE_EQ|INE002A01018", "NSE_FO|36702") is the unique ID.
  `exchange_token` can be reused after expiry, so it is never used as a key.
* NSE and BSE keys are different strings for the same company; we never map
  one onto the other implicitly (cross-venue comparison is explicit by ISIN).
* `expiry` is epoch milliseconds.
* `tick_size` in the JSON is expressed in paise (sample: 5.0 for a ₹0.05 tick).
  We convert to rupees and keep the raw value; `verify_tick_size` cross-checks
  against live prices at runtime so a format change is detected, not assumed.
"""
from __future__ import annotations

import gzip
import io
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

import pandas as pd

from .calendar import IST

BOD_URLS = {
    "NSE": "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz",
    "BSE": "https://assets.upstox.com/market-quote/instruments/exchange/BSE.json.gz",
    "complete": "https://assets.upstox.com/market-quote/instruments/exchange/complete.json.gz",
}
MIS_URLS = {
    "NSE": "https://assets.upstox.com/market-quote/instruments/exchange/NSE_MIS.json.gz",
    "BSE": "https://assets.upstox.com/market-quote/instruments/exchange/BSE_MIS.json.gz",
}
SUPPORTED_SEGMENTS = {"NSE_EQ", "BSE_EQ", "NSE_INDEX", "BSE_INDEX", "NSE_FO", "BSE_FO"}


@dataclass
class Instrument:
    instrument_key: str
    exchange: str
    segment: str
    instrument_type: str
    trading_symbol: str
    name: str = ""
    isin: str = ""
    exchange_token: str = ""
    lot_size: int = 1
    tick_size: float = 0.05      # rupees
    freeze_quantity: float = 0.0
    expiry: str | None = None    # YYYY-MM-DD (IST)
    strike: float | None = None
    option_type: str | None = None  # CE / PE
    underlying_key: str | None = None
    underlying_symbol: str | None = None
    weekly: int = 0
    security_type: str = ""

    @property
    def is_derivative(self) -> bool:
        return self.segment.endswith("_FO")

    @property
    def is_option(self) -> bool:
        return self.option_type in ("CE", "PE")


def normalize_record(r: dict) -> Instrument | None:
    seg = r.get("segment", "")
    if seg not in SUPPORTED_SEGMENTS:
        return None
    key = r.get("instrument_key")
    if not key or "|" not in key:
        return None
    itype = r.get("instrument_type", "")
    expiry = None
    if r.get("expiry"):
        try:
            expiry = datetime.fromtimestamp(int(r["expiry"]) / 1000, tz=timezone.utc).astimezone(IST).date().isoformat()
        except (ValueError, TypeError, OSError):
            expiry = None
    raw_tick = r.get("tick_size")
    tick = round(float(raw_tick) / 100.0, 4) if raw_tick not in (None, "") else 0.05
    opt = itype if itype in ("CE", "PE") else None
    strike = float(r["strike_price"]) if opt and r.get("strike_price") is not None else None
    return Instrument(
        instrument_key=key, exchange=r.get("exchange", seg.split("_")[0]), segment=seg,
        instrument_type=itype, trading_symbol=r.get("trading_symbol", ""), name=r.get("name", ""),
        isin=r.get("isin", "") or "", exchange_token=str(r.get("exchange_token", "")),
        lot_size=int(r.get("lot_size") or 1), tick_size=tick,
        freeze_quantity=float(r.get("freeze_quantity") or 0), expiry=expiry, strike=strike, option_type=opt,
        underlying_key=r.get("underlying_key"), underlying_symbol=r.get("underlying_symbol"),
        weekly=int(bool(r.get("weekly"))), security_type=r.get("security_type", "") or "",
    )


def parse_bod_bytes(blob: bytes) -> list[Instrument]:
    if blob[:2] == b"\x1f\x8b":
        blob = gzip.decompress(blob)
    data = json.load(io.BytesIO(blob))
    out = []
    for r in data:
        ins = normalize_record(r)
        if ins:
            out.append(ins)
    return out


def download_bod(exchange: str = "NSE", session=None, timeout: int = 60) -> list[Instrument]:
    import requests
    s = session or requests.Session()
    resp = s.get(BOD_URLS[exchange], timeout=timeout)
    resp.raise_for_status()
    return parse_bod_bytes(resp.content)


class InstrumentMaster:
    def __init__(self, db):
        self.db = db
        self._cache: dict[str, Instrument] = {}

    def store(self, instruments: list[Instrument]) -> int:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        rows = [(i.instrument_key, i.exchange, i.segment, i.instrument_type, i.trading_symbol, i.name, i.isin,
                 i.exchange_token, i.lot_size, i.tick_size, i.freeze_quantity, i.expiry, i.strike, i.option_type,
                 i.underlying_key, i.underlying_symbol, i.weekly, i.security_type, now) for i in instruments]
        with self.db.tx() as c:
            c.executemany("INSERT OR REPLACE INTO instruments VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
        self._cache.clear()
        return len(rows)

    def purge_expired(self, today: str) -> int:
        cur = self.db.execute("DELETE FROM instruments WHERE expiry IS NOT NULL AND expiry < ?", (today,))
        self._cache.clear()
        return cur.rowcount

    def get(self, key: str) -> Instrument | None:
        if key in self._cache:
            return self._cache[key]
        r = self.db.query("SELECT * FROM instruments WHERE instrument_key=?", (key,))
        if not r:
            return None
        d = r[0]
        d.pop("updated_at", None)
        ins = Instrument(**d)
        self._cache[key] = ins
        return ins

    def search(self, text: str, segments: tuple[str, ...] | None = None, limit: int = 50) -> pd.DataFrame:
        sql = ("SELECT instrument_key, exchange, segment, instrument_type, trading_symbol, name, lot_size, tick_size,"
               " expiry, strike, option_type FROM instruments WHERE (trading_symbol LIKE ? OR name LIKE ? OR isin=?)")
        p: list = [f"%{text.upper()}%", f"%{text.upper()}%", text.upper()]
        if segments:
            sql += f" AND segment IN ({','.join('?'*len(segments))})"
            p += list(segments)
        sql += " ORDER BY segment, expiry, strike LIMIT ?"
        p.append(limit)
        return pd.DataFrame(self.db.query(sql, p))

    def contracts(self, underlying_symbol: str, kind: str = "FUT") -> pd.DataFrame:
        if kind == "FUT":
            sql = "SELECT * FROM instruments WHERE underlying_symbol=? AND instrument_type='FUT' ORDER BY expiry"
        else:
            sql = ("SELECT * FROM instruments WHERE underlying_symbol=? AND option_type IS NOT NULL "
                   "ORDER BY expiry, strike, option_type")
        return pd.DataFrame(self.db.query(sql, (underlying_symbol.upper(),)))

    def expiries(self, underlying_symbol: str) -> list[str]:
        r = self.db.query("SELECT DISTINCT expiry FROM instruments WHERE underlying_symbol=? AND expiry IS NOT NULL "
                          "ORDER BY expiry", (underlying_symbol.upper(),))
        return [x["expiry"] for x in r]

    def front_future(self, underlying_symbol: str, today: str, roll_days: int = 3) -> Instrument | None:
        """Nearest future, rolling to the next contract `roll_days` calendar days before expiry."""
        from datetime import date, timedelta
        cutoff = (date.fromisoformat(today) + timedelta(days=roll_days)).isoformat()
        r = self.db.query("SELECT instrument_key FROM instruments WHERE underlying_symbol=? AND instrument_type='FUT'"
                          " AND expiry > ? ORDER BY expiry LIMIT 1", (underlying_symbol.upper(), cutoff))
        return self.get(r[0]["instrument_key"]) if r else None

    def by_isin(self, isin: str) -> list[Instrument]:
        r = self.db.query("SELECT instrument_key FROM instruments WHERE isin=? AND segment IN ('NSE_EQ','BSE_EQ')",
                          (isin,))
        return [self.get(x["instrument_key"]) for x in r]

    def count(self) -> dict:
        return {r["segment"]: r["n"] for r in self.db.query("SELECT segment, COUNT(*) n FROM instruments GROUP BY segment")}


def round_to_tick(price: float, tick: float, side: str = "nearest") -> float:
    import math
    if tick <= 0:
        return round(price, 2)
    q = price / tick
    if side == "up":
        q = math.ceil(q - 1e-9)
    elif side == "down":
        q = math.floor(q + 1e-9)
    else:
        q = round(q)
    return round(q * tick, 4)


def is_valid_tick(price: float, tick: float) -> bool:
    return abs(round(price / tick) * tick - price) < 1e-6


def verify_tick_size(ins: Instrument, live_prices: list[float]) -> bool:
    """Sanity check: live traded prices must sit on the tick grid we derived."""
    return all(is_valid_tick(p, ins.tick_size) for p in live_prices if p)


def instrument_to_dict(ins: Instrument) -> dict:
    return asdict(ins)
