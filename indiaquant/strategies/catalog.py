"""Implemented strategies with explicit, testable rules.

Evidence labels used in `evidence`:
  THEORY    – established financial theory / widely documented mechanism
  PUBLISHED – empirical results reported in peer-reviewed or well-known research (not re-verified here)
  UNVERIFIED– practitioner folklore; treat as a hypothesis until measured on real data
Measured results live only in reports produced by `research` runs on real data.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..analytics import indicators as ind
from ..data.calendar import parse_hhmm
from .base import Strategy


def _frame(df):
    return pd.DataFrame({"entry": False, "exit": False, "stop": np.nan, "target": np.nan, "why": ""}, index=df.index)


def _p(self, params):
    p = dict(self.params)
    p.update(params or {})
    return p


# ------------------------------------------------------------------ TREND / SWING
class SMACrossover(Strategy):
    def generate(self, df, params=None, context=None):
        p = _p(self, params)
        f, s = ind.sma(df["close"], p["fast"]), ind.sma(df["close"], p["slow"])
        a = ind.atr(df, 14)
        out = _frame(df)
        up = (f > s) & (f.shift() <= s.shift())
        dn = (f < s) & (f.shift() >= s.shift())
        out["entry"] = up.fillna(False)
        out["exit"] = dn.fillna(False)
        out["stop"] = df["close"] - p["atr_stop"] * a
        out.loc[out["entry"], "why"] = [f"SMA{p['fast']} {x:.2f} crossed above SMA{p['slow']} {y:.2f}"
                                       for x, y in zip(f[out["entry"]], s[out["entry"]])]
        return out


class EMAADXTrend(Strategy):
    def generate(self, df, params=None, context=None):
        p = _p(self, params)
        c = df["close"]
        e1, e2, ax, a = ind.ema(c, p["fast"]), ind.ema(c, p["slow"]), ind.adx(df, 14), ind.atr(df, 14)
        cond = (c > e1) & (e1 > e2) & (ax > p["adx_min"])
        out = _frame(df)
        out["entry"] = (cond & ~cond.shift(fill_value=False)).fillna(False)
        out["exit"] = (c < e1).fillna(False)
        out["stop"] = c - p["atr_stop"] * a
        out.loc[out["entry"], "why"] = [f"close>EMA{p['fast']}>EMA{p['slow']}, ADX {v:.1f}>{p['adx_min']}"
                                       for v in ax[out["entry"]]]
        return out


class DonchianBreakout(Strategy):
    def generate(self, df, params=None, context=None):
        p = _p(self, params)
        lo_x, hi = ind.donchian(df, p["entry_n"])
        lo, _ = ind.donchian(df, p["exit_n"])
        vr = ind.volume_ratio(df["volume"], 20)
        a = ind.atr(df, 14)
        out = _frame(df)
        out["entry"] = ((df["close"] > hi) & (vr >= p["vol_mult"])).fillna(False)
        out["exit"] = (df["close"] < lo).fillna(False)
        out["stop"] = df["close"] - p["atr_stop"] * a
        out.loc[out["entry"], "why"] = [f"close {c:.2f} > prior {p['entry_n']}-bar high {h:.2f}; volume {v:.1f}x avg"
                                       for c, h, v in zip(df["close"][out["entry"]], hi[out["entry"]],
                                                          vr[out["entry"]])]
        return out


class RelativeStrength(Strategy):
    def generate(self, df, params=None, context=None):
        p = _p(self, params)
        out = _frame(df)
        bench = (context or {}).get("benchmark")
        if bench is None or len(bench) == 0:
            out["why"] = ""
            return out  # no benchmark -> never signals (no fabricated benchmark)
        rs = ind.relative_strength(df["close"], bench["close"], p["lookback"])
        trend = df["close"] > ind.sma(df["close"], p["trend_n"])
        cond = (rs > p["rs_min"]) & trend
        a = ind.atr(df, 14)
        out["entry"] = (cond & ~cond.shift(fill_value=False)).fillna(False)
        out["exit"] = ((rs < 0) | (df["close"] < ind.sma(df["close"], p["trend_n"]))).fillna(False)
        out["stop"] = df["close"] - p["atr_stop"] * a
        out.loc[out["entry"], "why"] = [f"{p['lookback']}-bar return beats benchmark by {x:.1%}; above SMA{p['trend_n']}"
                                       for x in rs[out["entry"]]]
        return out


class PullbackTrend(Strategy):
    def generate(self, df, params=None, context=None):
        p = _p(self, params)
        c = df["close"]
        r2 = ind.rsi(c, p["rsi_n"])
        long_trend = c > ind.sma(c, p["trend_n"])
        a = ind.atr(df, 14)
        out = _frame(df)
        out["entry"] = (long_trend & (r2 < p["rsi_entry"])).fillna(False)
        out["exit"] = (c > ind.sma(c, p["exit_sma"])).fillna(False)
        out["stop"] = c - p["atr_stop"] * a
        out.loc[out["entry"], "why"] = [f"uptrend (>SMA{p['trend_n']}) pullback: RSI{p['rsi_n']}={v:.1f}<{p['rsi_entry']}"
                                       for v in r2[out["entry"]]]
        return out


# ---------------------------------------------------------------- MEAN REVERSION
class RSIReversion(Strategy):
    def generate(self, df, params=None, context=None):
        p = _p(self, params)
        c = df["close"]
        r = ind.rsi(c, p["rsi_n"])
        a = ind.atr(df, 14)
        filt = (c > ind.sma(c, p["trend_n"])) if p.get("trend_filter") else pd.Series(True, index=df.index)
        cross = (r < p["oversold"]) & (r.shift() >= p["oversold"])
        out = _frame(df)
        out["entry"] = (cross & filt).fillna(False)
        out["exit"] = (r > p["exit_level"]).fillna(False)
        out["stop"] = c - p["atr_stop"] * a
        out.loc[out["entry"], "why"] = [f"RSI{p['rsi_n']} fell below {p['oversold']} ({v:.1f})" for v in r[out["entry"]]]
        return out


class BollingerReversion(Strategy):
    def generate(self, df, params=None, context=None):
        p = _p(self, params)
        c = df["close"]
        lo, mid, hi = ind.bollinger(c, p["n"], p["k"])
        a = ind.atr(df, 14)
        out = _frame(df)
        out["entry"] = ((c < lo) & (c.shift() >= lo.shift())).fillna(False)
        out["exit"] = (c >= mid).fillna(False)
        out["stop"] = c - p["atr_stop"] * a
        out["target"] = mid
        out.loc[out["entry"], "why"] = [f"close {x:.2f} below lower band {y:.2f}" for x, y in
                                       zip(c[out["entry"]], lo[out["entry"]])]
        return out


class ZScoreReversion(Strategy):
    def generate(self, df, params=None, context=None):
        p = _p(self, params)
        z = ind.zscore(df["close"], p["n"])
        a = ind.atr(df, 14)
        out = _frame(df)
        out["entry"] = ((z < -p["z_entry"]) & (z.shift() >= -p["z_entry"])).fillna(False)
        out["exit"] = (z > p["z_exit"]).fillna(False)
        out["stop"] = df["close"] - p["atr_stop"] * a
        out.loc[out["entry"], "why"] = [f"z-score {v:.2f} < -{p['z_entry']}" for v in z[out["entry"]]]
        return out


# --------------------------------------------------------------------- INTRADAY
def _intraday_gate(df, p):
    t = pd.Series([x.time() for x in df.index], index=df.index)
    return t <= parse_hhmm(p.get("entry_cutoff", "14:45"))


class OpeningRangeBreakout(Strategy):
    def generate(self, df, params=None, context=None):
        p = _p(self, params)
        orng = ind.opening_range(df, p["or_minutes"])
        vw = ind.session_vwap(df)
        vr = ind.volume_ratio(df["volume"], 20)
        c = df["close"]
        day = pd.Series(df.index.date, index=df.index)
        brk = (c > orng["or_high"]) & (c > vw) & (vr >= p["vol_mult"]) & _intraday_gate(df, p)
        first = brk & (brk.groupby(day).cumsum() == 1)       # one entry per day
        rng = orng["or_high"] - orng["or_low"]
        out = _frame(df)
        out["entry"] = first.fillna(False)
        out["exit"] = (c < vw).fillna(False)
        out["stop"] = orng["or_low"]
        out["target"] = c + p["r_mult"] * (c - orng["or_low"])
        ok_width = (rng / c) <= p["max_range_pct"]
        out["entry"] &= ok_width.fillna(False)
        out.loc[out["entry"], "why"] = [f"{p['or_minutes']}m opening-range high {h:.2f} broken; above VWAP {w:.2f}; vol {v:.1f}x"
                                       for h, w, v in zip(orng["or_high"][out["entry"]], vw[out["entry"]],
                                                          vr[out["entry"]])]
        return out


class VWAPReversion(Strategy):
    def generate(self, df, params=None, context=None):
        p = _p(self, params)
        c = df["close"]
        vw = ind.session_vwap(df)
        dev = (c - vw) / vw
        sd = dev.rolling(p["n"], min_periods=p["n"]).std()
        z = dev / sd
        a = ind.atr(df, 14)
        out = _frame(df)
        trig = (z < -p["z_entry"]) & (ind.minutes_since_open_series(df) >= 30) & _intraday_gate(df, p)
        out["entry"] = (trig & ~trig.shift(fill_value=False)).fillna(False)
        out["exit"] = (c >= vw).fillna(False)
        out["stop"] = c - p["atr_stop"] * a
        out["target"] = vw
        out.loc[out["entry"], "why"] = [f"price {x:.2%} below VWAP (z={v:.2f})" for x, v in
                                       zip(dev[out["entry"]], z[out["entry"]])]
        return out


class PrevDayBreakout(Strategy):
    def generate(self, df, params=None, context=None):
        p = _p(self, params)
        day = pd.Series(df.index.date, index=df.index)
        dh = df["high"].groupby(day).max()
        prev_high = day.map(dh.shift(1))
        c = df["close"]
        vw = ind.session_vwap(df)
        mins = ind.minutes_since_open_series(df)
        brk = (c > prev_high) & (mins >= p["wait_minutes"]) & (c > vw) & _intraday_gate(df, p)
        first = brk & (brk.groupby(day).cumsum() == 1)
        a = ind.atr(df, 14)
        out = _frame(df)
        out["entry"] = first.fillna(False)
        out["exit"] = (c < vw).fillna(False)
        out["stop"] = np.minimum(prev_high - p["atr_buffer"] * a, c - p["atr_buffer"] * a)
        out.loc[out["entry"], "why"] = [f"broke previous-day high {h:.2f} after {p['wait_minutes']}m; above VWAP"
                                       for h in prev_high[out["entry"]]]
        return out


COMMON_SWING = dict(style="swing", timeframe="1d")
COMMON_INTRA = dict(style="intraday", timeframe="1m")

REGISTRY: dict[str, Strategy] = {s.name: s for s in [
    SMACrossover(
        name="sma_crossover", family="trend", **COMMON_SWING,
        hypothesis="Prices exhibit time-series momentum; a fast MA crossing a slow MA marks trend onset.",
        rationale="Under-reaction to information and herding create persistent trends.",
        entry_rule="Buy next open when SMA(fast) crosses above SMA(slow) at close.",
        exit_rule="Sell next open when SMA(fast) crosses below SMA(slow), or stop hit.",
        stop_rule="Initial stop = close - atr_stop × ATR(14).",
        evidence="PUBLISHED: time-series momentum (Moskowitz, Ooi & Pedersen 2012); MA rules (Brock, Lakonishok & "
                 "LeBaron 1992) — later studies find much weaker results after costs.",
        fails_when="Choppy/sideways markets cause repeated whipsaws; costs dominate on small capital.",
        params={"fast": 20, "slow": 50, "atr_stop": 2.0},
        param_grid={"fast": [10, 20, 30], "slow": [50, 100], "atr_stop": [2.0, 3.0]}),
    EMAADXTrend(
        name="ema_adx_trend", family="trend", **COMMON_SWING,
        hypothesis="Aligned EMAs plus ADX>threshold filter for established trends.",
        rationale="ADX measures directional strength; filtering weak trends should reduce whipsaws.",
        entry_rule="Buy when close>EMA(fast)>EMA(slow) and ADX>adx_min (first bar of condition).",
        exit_rule="Sell when close<EMA(fast).", stop_rule="close - atr_stop × ATR(14).",
        evidence="UNVERIFIED: widely used practitioner filter (Wilder 1978); limited rigorous evidence.",
        fails_when="Late entries near trend exhaustion; ADX lags.",
        params={"fast": 20, "slow": 50, "adx_min": 25, "atr_stop": 2.0},
        param_grid={"adx_min": [20, 25, 30], "fast": [10, 20]}),
    DonchianBreakout(
        name="donchian_breakout", family="breakout", **COMMON_SWING,
        hypothesis="Closes beyond the N-bar range with volume expansion start new trends.",
        rationale="Breakouts force stop/limit order flow; volume confirms participation.",
        entry_rule="Buy when close > prior entry_n-bar high and volume ≥ vol_mult × 20-bar avg.",
        exit_rule="Sell when close < prior exit_n-bar low.", stop_rule="close - atr_stop × ATR(14).",
        evidence="PUBLISHED/THEORY: 'Turtle' channel breakouts; trend-following literature (Hurst, Ooi & Pedersen 2017).",
        fails_when="False breakouts in range-bound markets; gaps through stops.",
        params={"entry_n": 20, "exit_n": 10, "vol_mult": 1.5, "atr_stop": 2.0},
        param_grid={"entry_n": [20, 55], "exit_n": [10, 20], "vol_mult": [1.0, 1.5]}),
    RelativeStrength(
        name="relative_strength", family="trend", **COMMON_SWING, needs_benchmark=True,
        hypothesis="Stocks outperforming the index tend to keep outperforming (cross-sectional momentum).",
        rationale="Momentum anomaly, documented in Indian equities as well.",
        entry_rule="Buy when lookback return − benchmark lookback return > rs_min and close>SMA(trend_n).",
        exit_rule="Sell when relative strength < 0 or close < SMA(trend_n).", stop_rule="close - atr_stop × ATR(14).",
        evidence="PUBLISHED: Jegadeesh & Titman (1993); Indian evidence e.g. Sehgal & Balakrishnan (2002).",
        fails_when="Momentum crashes after sharp market reversals (Daniel & Moskowitz 2016).",
        params={"lookback": 63, "trend_n": 50, "rs_min": 0.02, "atr_stop": 2.5},
        param_grid={"lookback": [63, 126], "rs_min": [0.0, 0.02, 0.05]}),
    PullbackTrend(
        name="pullback_trend", family="trend", **COMMON_SWING,
        hypothesis="Short-term oversold dips inside long-term uptrends tend to recover.",
        rationale="Short-horizon reversal combined with long-horizon momentum.",
        entry_rule="Buy when close>SMA(trend_n) and RSI(rsi_n)<rsi_entry.",
        exit_rule="Sell when close > SMA(exit_sma).", stop_rule="close - atr_stop × ATR(14).",
        evidence="UNVERIFIED/PUBLISHED-practitioner: Connors & Alvarez (2009) RSI(2) rules; short-term reversal "
                 "(Lehmann 1990).",
        fails_when="Trend breaks down; dips keep falling (catching knives).",
        params={"rsi_n": 2, "rsi_entry": 10, "trend_n": 200, "exit_sma": 5, "atr_stop": 3.0},
        param_grid={"rsi_entry": [5, 10, 15], "trend_n": [100, 200]}),
    RSIReversion(
        name="rsi_reversion", family="mean_reversion", **COMMON_SWING,
        hypothesis="RSI below an oversold threshold mean-reverts.",
        rationale="Liquidity-provision / over-reaction argument.",
        entry_rule="Buy when RSI(rsi_n) crosses below oversold (optionally only above SMA(trend_n)).",
        exit_rule="Sell when RSI > exit_level.", stop_rule="close - atr_stop × ATR(14).",
        evidence="UNVERIFIED: standard technical rule; academic support for short-term reversal is mixed.",
        fails_when="Strong downtrends; news-driven repricing.",
        params={"rsi_n": 14, "oversold": 30, "exit_level": 55, "trend_filter": True, "trend_n": 200, "atr_stop": 2.5},
        param_grid={"oversold": [25, 30, 35], "exit_level": [50, 60]}),
    BollingerReversion(
        name="bollinger_reversion", family="mean_reversion", **COMMON_SWING,
        hypothesis="Closes below the lower Bollinger band revert toward the mean.",
        rationale="Statistical excursion from a rolling mean under range-bound conditions.",
        entry_rule="Buy when close crosses below lower band (n, k).", exit_rule="Sell when close ≥ middle band.",
        stop_rule="close - atr_stop × ATR(14).",
        evidence="UNVERIFIED: Bollinger (2001); assumes approximate stationarity which trends violate.",
        fails_when="Volatility expansion and trending phases ('walking the band').",
        params={"n": 20, "k": 2.0, "atr_stop": 2.5}, param_grid={"n": [20, 30], "k": [2.0, 2.5]}),
    ZScoreReversion(
        name="zscore_reversion", family="mean_reversion", **COMMON_SWING,
        hypothesis="Price deviations beyond z standard deviations from a rolling mean revert.",
        rationale="Same as Bollinger; parameterised in z-units.",
        entry_rule="Buy when z(n) crosses below -z_entry.", exit_rule="Sell when z > z_exit.",
        stop_rule="close - atr_stop × ATR(14).", evidence="UNVERIFIED.",
        fails_when="Non-stationary prices (most single stocks).",
        params={"n": 20, "z_entry": 2.0, "z_exit": 0.0, "atr_stop": 2.5},
        param_grid={"z_entry": [1.5, 2.0, 2.5]}),
    OpeningRangeBreakout(
        name="orb", family="breakout", **COMMON_INTRA,
        hypothesis="Breaks of the first N-minute range with VWAP and volume confirmation continue intraday.",
        rationale="Opening auction resolves overnight information; follow-through as late participants enter.",
        entry_rule="After or_minutes, first close above OR high, above session VWAP, volume ≥ vol_mult×avg, "
                   "before entry_cutoff; range width ≤ max_range_pct.",
        exit_rule="Close below VWAP, target r_mult×risk, stop OR low, or forced square-off.",
        stop_rule="Opening-range low.",
        evidence="PUBLISHED: Zarattini, Barbon & Aziz (2023/24) report ORB results on US stocks; Indian evidence "
                 "not established — UNVERIFIED for NSE.",
        fails_when="Low-volatility days; false breakouts; wide ranges make risk too large.",
        params={"or_minutes": 15, "vol_mult": 1.2, "r_mult": 2.0, "max_range_pct": 0.02, "entry_cutoff": "14:45"},
        param_grid={"or_minutes": [15, 30], "vol_mult": [1.0, 1.5], "r_mult": [1.5, 2.0]}),
    VWAPReversion(
        name="vwap_reversion", family="mean_reversion", **COMMON_INTRA,
        hypothesis="Large intraday deviations below VWAP revert toward VWAP.",
        rationale="VWAP anchors institutional execution benchmarks.",
        entry_rule="z-score of (close−VWAP)/VWAP over n bars < −z_entry, ≥30 min after open, before cutoff.",
        exit_rule="Close ≥ VWAP, stop, or forced square-off.", stop_rule="close − atr_stop × ATR(14 bars).",
        evidence="UNVERIFIED.", fails_when="Trend days (price walks away from VWAP all session).",
        params={"n": 30, "z_entry": 2.0, "atr_stop": 2.0, "entry_cutoff": "14:45"},
        param_grid={"z_entry": [1.5, 2.0, 2.5], "n": [30, 60]}),
    PrevDayBreakout(
        name="prev_day_breakout", family="breakout", **COMMON_INTRA,
        hypothesis="Breaking the previous day's high after the open settles signals continuation.",
        rationale="Previous-day extremes are widely watched reference levels.",
        entry_rule="First close above previous-day high after wait_minutes, above VWAP, before cutoff.",
        exit_rule="Close below VWAP, stop, or forced square-off.",
        stop_rule="min(prev high, close) − atr_buffer × ATR(14 bars).", evidence="UNVERIFIED.",
        fails_when="Failed breakouts (see STOCKSHIELD false-breakout flag).",
        params={"wait_minutes": 15, "atr_buffer": 1.0, "entry_cutoff": "14:45"},
        param_grid={"wait_minutes": [15, 30], "atr_buffer": [0.5, 1.0]}),
]}


def get_strategy(name: str) -> Strategy:
    return REGISTRY[name]


def list_strategies() -> list[dict]:
    return [s.describe() for s in REGISTRY.values()]
