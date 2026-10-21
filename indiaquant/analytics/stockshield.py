"""STOCKSHIELD — market-integrity & retail-risk intelligence.

This module scores OBSERVABLE patterns that are associated in the literature
and in SEBI/exchange surveillance practice with elevated retail risk (abnormal
volume, price spikes, rapid reversals, false breakouts, liquidity loss). It
does NOT detect or allege manipulation by anyone. Every score is an additive,
transparent sum of feature contributions with the observed values attached.

Observed  = measured directly from candles/quotes.
Inferred  = a possible explanation; always phrased as a hypothesis.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .indicators import atr, donchian, volume_ratio, zscore


@dataclass
class ShieldReport:
    score: float                       # 0-100, heuristic, uncalibrated
    level: str                         # LOW / ELEVATED / HIGH
    contributions: dict                # feature -> points
    observed: dict                     # feature -> measured value
    hypotheses: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)


WEIGHTS = {
    "abnormal_volume": 20, "price_spike": 15, "price_volume_divergence": 15, "rapid_reversal": 15,
    "false_breakout": 15, "liquidity_deterioration": 10, "volatility_expansion": 10,
}


def _clip01(x):
    return float(np.clip(x, 0, 1)) if pd.notna(x) else 0.0


def analyze(df: pd.DataFrame, spread_pct: float | None = None) -> ShieldReport:
    if len(df) < 40:
        return ShieldReport(0, "INSUFFICIENT_DATA", {}, {}, [], ["need >= 40 bars"])
    c, v = df["close"], df["volume"]
    ret = c.pct_change()
    vr = volume_ratio(v, 20).iloc[-1]
    rz = zscore(ret, 60).iloc[-1]
    # divergence: big volume with little net progress over 5 bars
    prog5 = abs(c.iloc[-1] / c.iloc[-6] - 1) if len(c) > 6 else np.nan
    a = (atr(df, 14) / c).iloc[-1]
    vol5 = v.iloc[-5:].mean() / v.iloc[-25:-5].mean() if v.iloc[-25:-5].mean() > 0 else np.nan
    divergence = (vol5 - 1) / 2 if prog5 < a else 0.0
    # rapid reversal: a >2 ATR move in last 5 bars that has retraced >60%
    w = c.iloc[-6:]
    ext = w.max() if abs(w.max() - w.iloc[0]) > abs(w.min() - w.iloc[0]) else w.min()
    move = ext - w.iloc[0]
    retr = (ext - w.iloc[-1]) / move if move else 0.0
    big = abs(move) / c.iloc[-6] > 2 * a if a == a else False
    reversal = retr if big and retr > 0.6 else 0.0
    # false breakout: closed above prior 20-bar high within last 5 bars, now back below it
    lo, hi = donchian(df, 20)
    fb = 0.0
    for i in range(-5, 0):
        if c.iloc[i] > hi.iloc[i] and c.iloc[-1] < hi.iloc[i]:
            fb = 1.0
            break
        if c.iloc[i] < lo.iloc[i] and c.iloc[-1] > lo.iloc[i]:
            fb = 1.0
            break
    zero_frac = (v.iloc[-20:] == 0).mean()
    liq = max(zero_frac * 2, 0.0)
    if spread_pct is not None:
        liq = max(liq, spread_pct / 0.01)
    rv_now = ret.iloc[-10:].std()
    rv_base = ret.iloc[-70:-10].std()
    vexp = (rv_now / rv_base - 1) if rv_base and rv_base > 0 else 0.0

    feats = {
        "abnormal_volume": _clip01((vr - 2) / 3),          # 2x avg -> 0, 5x -> 1
        "price_spike": _clip01((abs(rz) - 2) / 2),         # |z| 2 -> 0, 4 -> 1
        "price_volume_divergence": _clip01(divergence),
        "rapid_reversal": _clip01(reversal),
        "false_breakout": fb,
        "liquidity_deterioration": _clip01(liq),
        "volatility_expansion": _clip01(vexp / 2),
    }
    contrib = {k: round(WEIGHTS[k] * x, 2) for k, x in feats.items()}
    score = round(sum(contrib.values()), 1)
    level = "HIGH" if score >= 50 else "ELEVATED" if score >= 25 else "LOW"
    observed = {"volume_vs_20bar_avg": round(float(vr), 2) if pd.notna(vr) else None,
                "return_zscore_60": round(float(rz), 2) if pd.notna(rz) else None,
                "net_progress_5bar_pct": round(float(prog5) * 100, 2) if pd.notna(prog5) else None,
                "atr_pct": round(float(a) * 100, 2) if pd.notna(a) else None,
                "retracement_of_recent_move": round(float(retr), 2),
                "zero_volume_bar_frac_20": round(float(zero_frac), 2),
                "spread_pct": spread_pct, "short_vs_base_vol_ratio": round(float(vexp + 1), 2)}
    hyp = []
    if feats["abnormal_volume"] > 0.5 and feats["price_volume_divergence"] > 0.3:
        hyp.append("Hypothesis: heavy turnover without price progress can reflect distribution, absorption, "
                   "or news-driven repositioning. Not evidence of wrongdoing.")
    if feats["false_breakout"]:
        hyp.append("Hypothesis: failed breakout — late breakout buyers may be trapped; elevated reversal risk.")
    if feats["rapid_reversal"] > 0.5:
        hyp.append("Hypothesis: sharp spike that quickly retraced; liquidity may have been thin at the extreme.")
    lim = ["Heuristic weights, not calibrated to outcomes.",
           "Candle data cannot show order-level intent; order-book depth (top-5) is not proof of 'whale' activity.",
           "Check exchange surveillance (ASM/GSM) lists and company announcements before drawing conclusions."]
    return ShieldReport(score, level, contrib, observed, hyp, lim)
