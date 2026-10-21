"""Technical indicators. All are causal: value at bar t uses data up to and including t only."""
from __future__ import annotations

import numpy as np
import pandas as pd


def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=n).mean()


def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False, min_periods=n).mean()


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    """Wilder's RSI."""
    d = close.diff()
    up = d.clip(lower=0)
    dn = -d.clip(upper=0)
    au = up.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    ad = dn.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    rs = au / ad.replace(0, np.nan)
    out = 100 - 100 / (1 + rs)
    out = out.where(ad != 0, 100.0)
    return out.where(au.notna())


def true_range(df: pd.DataFrame) -> pd.Series:
    pc = df["close"].shift()
    return pd.concat([df["high"] - df["low"], (df["high"] - pc).abs(), (df["low"] - pc).abs()], axis=1).max(axis=1)


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    return true_range(df).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def bollinger(close: pd.Series, n: int = 20, k: float = 2.0):
    m = sma(close, n)
    sd = close.rolling(n, min_periods=n).std(ddof=0)
    return m - k * sd, m, m + k * sd


def zscore(s: pd.Series, n: int = 20) -> pd.Series:
    m = s.rolling(n, min_periods=n).mean()
    sd = s.rolling(n, min_periods=n).std(ddof=0)
    return (s - m) / sd.replace(0, np.nan)


def donchian(df: pd.DataFrame, n: int = 20):
    """Channel of the PRIOR n bars (shifted) so a breakout compares against the past only."""
    hi = df["high"].rolling(n, min_periods=n).max().shift(1)
    lo = df["low"].rolling(n, min_periods=n).min().shift(1)
    return lo, hi


def adx(df: pd.DataFrame, n: int = 14) -> pd.Series:
    up = df["high"].diff()
    dn = -df["low"].diff()
    plus_dm = np.where((up > dn) & (up > 0), up, 0.0)
    minus_dm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = true_range(df)
    atr_ = tr.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    pdi = 100 * pd.Series(plus_dm, index=df.index).ewm(alpha=1 / n, adjust=False, min_periods=n).mean() / atr_
    mdi = 100 * pd.Series(minus_dm, index=df.index).ewm(alpha=1 / n, adjust=False, min_periods=n).mean() / atr_
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return dx.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def session_vwap(df: pd.DataFrame) -> pd.Series:
    """Intraday VWAP that resets each session (IST date)."""
    tp = (df["high"] + df["low"] + df["close"]) / 3
    day = df.index.date
    pv = (tp * df["volume"]).groupby(day).cumsum()
    vv = df["volume"].groupby(day).cumsum()
    return pv / vv.replace(0, np.nan)


def opening_range(df: pd.DataFrame, minutes: int = 15) -> pd.DataFrame:
    """Per-bar opening-range high/low, available only AFTER the range window closes (NaN before)."""
    from ..data.calendar import minutes_since_open
    ms = pd.Series([minutes_since_open(t) for t in df.index], index=df.index)
    in_rng = ms < minutes
    day = pd.Series(df.index.date, index=df.index)
    hi = df["high"].where(in_rng).groupby(day).transform("max")
    lo = df["low"].where(in_rng).groupby(day).transform("min")
    hi = hi.where(~in_rng)
    lo = lo.where(~in_rng)
    return pd.DataFrame({"or_high": hi, "or_low": lo, "mins": ms})


def realized_vol(close: pd.Series, n: int = 20, periods_per_year: int = 252) -> pd.Series:
    return np.log(close).diff().rolling(n, min_periods=n).std() * np.sqrt(periods_per_year)


def relative_strength(close: pd.Series, bench: pd.Series, n: int = 63) -> pd.Series:
    b = bench.reindex(close.index).ffill()
    return close.pct_change(n) - b.pct_change(n)


def obv(df: pd.DataFrame) -> pd.Series:
    sign = np.sign(df["close"].diff()).fillna(0)
    return (sign * df["volume"]).cumsum()


def volume_ratio(vol: pd.Series, n: int = 20) -> pd.Series:
    """Volume vs. average of the PRIOR n bars."""
    return vol / vol.rolling(n, min_periods=n).mean().shift(1)


def minutes_since_open_series(df: pd.DataFrame) -> pd.Series:
    from ..data.calendar import minutes_since_open
    return pd.Series([minutes_since_open(t) for t in df.index], index=df.index)
