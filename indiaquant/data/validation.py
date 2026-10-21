"""Candle validation and data-quality checks."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .calendar import IST, MARKET_CLOSE, MARKET_OPEN


@dataclass
class QualityReport:
    rows: int = 0
    issues: list[tuple[str, str]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(k in ("ohlc_inconsistent", "negative", "nan") for k, _ in self.issues)

    def add(self, kind: str, detail: str):
        self.issues.append((kind, detail))


REQUIRED = ["open", "high", "low", "close", "volume"]


def validate_candles(df: pd.DataFrame, interval: str = "1d", check_gaps: bool = True) -> QualityReport:
    rep = QualityReport(rows=len(df))
    if df.empty:
        rep.add("empty", "no rows")
        return rep
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        rep.add("schema", f"missing columns {missing}")
        return rep
    if not df.index.is_monotonic_increasing:
        rep.add("unsorted", "index not increasing")
    dups = df.index.duplicated().sum()
    if dups:
        rep.add("duplicates", f"{dups} duplicate timestamps")
    if df[REQUIRED].isna().any().any():
        rep.add("nan", f"{int(df[REQUIRED].isna().sum().sum())} NaN values")
    if (df[["open", "high", "low", "close"]] <= 0).any().any() or (df["volume"] < 0).any():
        rep.add("negative", "non-positive price or negative volume")
    bad = (df["high"] < df[["open", "close"]].max(axis=1) - 1e-9) | (df["low"] > df[["open", "close"]].min(axis=1) + 1e-9) \
        | (df["high"] < df["low"])
    if bad.any():
        rep.add("ohlc_inconsistent", f"{int(bad.sum())} rows violate low<=open/close<=high")
    ret = df["close"].pct_change().abs()
    jumps = ret[ret > 0.25]
    if len(jumps):
        rep.add("large_jump", f"{len(jumps)} close-to-close moves >25% (possible split/bonus not adjusted, or bad tick)"
                f" first at {jumps.index[0]}")
    zero_vol = (df["volume"] == 0).mean()
    if zero_vol > 0.2:
        rep.add("low_liquidity", f"{zero_vol:.0%} of bars have zero volume")
    if check_gaps and interval.endswith("m") and len(df) > 2:
        mins = int(interval[:-1])
        idx = df.index
        if idx.tz is None:
            idx = idx.tz_localize(IST)
        else:
            idx = idx.tz_convert(IST)
        s = pd.Series(idx, index=idx)
        same_day = s.dt.date == s.shift().dt.date
        gap = (s - s.shift()).dt.total_seconds() / 60
        g = gap[same_day & (gap > mins * 1.5)]
        if len(g):
            rep.add("intraday_gaps", f"{len(g)} missing-bar gaps within sessions")
        t = s.dt.time
        outside = ((t < MARKET_OPEN) | (t >= MARKET_CLOSE)).sum()
        if outside:
            rep.add("outside_session", f"{int(outside)} bars outside 09:15-15:30 IST")
    return rep


def clean_candles(df: pd.DataFrame) -> pd.DataFrame:
    """Deterministic cleaning: sort, drop exact duplicate timestamps (keep last), drop NaN/invalid rows.
    Never fabricates or interpolates prices."""
    if df.empty:
        return df
    out = df[~df.index.duplicated(keep="last")].sort_index()
    out = out.dropna(subset=REQUIRED)
    good = (out["high"] >= out["low"]) & (out[["open", "high", "low", "close"]] > 0).all(axis=1)
    return out[good]


def is_fresh(last_ts, max_age_seconds: float, now=None) -> bool:
    import time
    if last_ts is None:
        return False
    if isinstance(last_ts, (int, float)):
        t = float(last_ts)
    else:
        t = pd.Timestamp(last_ts).timestamp()
    now = now if now is not None else time.time()
    return (now - t) <= max_age_seconds and (now - t) >= -5


def resample_ohlcv(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    if "oi" in df:
        agg["oi"] = "last"
    out = df.resample(rule, label="left", closed="left").agg(agg)
    return out.dropna(subset=["open"])


def data_hash(df: pd.DataFrame) -> str:
    import hashlib
    h = hashlib.sha256(pd.util.hash_pandas_object(df[REQUIRED].round(6), index=True).values.tobytes())
    return h.hexdigest()[:16]


def synthetic_ohlcv(n: int = 500, seed: int = 0, start: str = "2020-01-01", freq: str = "B", drift: float = 0.0003,
                    vol: float = 0.015, price: float = 100.0) -> pd.DataFrame:
    """SYNTHETIC TEST DATA ONLY (geometric random walk). Used exclusively by unit tests
    and the offline demo; every frame it produces carries source='SYNTHETIC_TEST_DATA'."""
    rng = np.random.default_rng(seed)
    r = rng.normal(drift, vol, n)
    close = price * np.exp(np.cumsum(r))
    open_ = np.r_[price, close[:-1]] * np.exp(rng.normal(0, vol / 4, n))
    hi = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, vol / 2, n)))
    lo = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, vol / 2, n)))
    v = rng.integers(50_000, 500_000, n).astype(float)
    idx = pd.date_range(start, periods=n, freq=freq, tz=IST)
    df = pd.DataFrame({"open": open_, "high": hi, "low": lo, "close": close, "volume": v, "oi": 0.0}, index=idx)
    df.attrs["source"] = "SYNTHETIC_TEST_DATA"
    return df


def synthetic_intraday(days: int = 20, seed: int = 0, price: float = 500.0) -> pd.DataFrame:
    """SYNTHETIC TEST DATA ONLY: 1-minute bars 09:15-15:29 IST."""
    rng = np.random.default_rng(seed)
    frames = []
    d0 = pd.Timestamp("2025-01-06", tz=IST)
    bdays = pd.bdate_range(d0, periods=days, tz=IST)
    p = price
    for d in bdays:
        idx = pd.date_range(d + pd.Timedelta(hours=9, minutes=15), periods=375, freq="1min")
        r = rng.normal(0, 0.0012, 375)
        close = p * np.exp(np.cumsum(r))
        open_ = np.r_[p * (1 + rng.normal(0, 0.003)), close[:-1]]
        hi = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, 0.0005, 375)))
        lo = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, 0.0005, 375)))
        v = rng.integers(1_000, 20_000, 375).astype(float)
        frames.append(pd.DataFrame({"open": open_, "high": hi, "low": lo, "close": close, "volume": v, "oi": 0.0},
                                   index=idx))
        p = close[-1]
    df = pd.concat(frames)
    df.attrs["source"] = "SYNTHETIC_TEST_DATA"
    return df
