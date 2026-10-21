"""Rule-based market-regime classifier built on measurable features.

Labels are derived from thresholds on causal features (no future data). The
output includes the raw feature values so every label is auditable. It is NOT
a probability; `score` fields are heuristic strengths, uncalibrated.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .indicators import adx, atr, ema, realized_vol, sma


@dataclass
class Regime:
    labels: list[str]
    features: dict
    notes: list[str] = field(default_factory=list)

    @property
    def primary(self) -> str:
        return self.labels[0] if self.labels else "UNCERTAIN"


def regime_features(df: pd.DataFrame) -> pd.DataFrame:
    c = df["close"]
    f = pd.DataFrame(index=df.index)
    f["ret_20"] = c.pct_change(20)
    f["ema_slope"] = ema(c, 50).pct_change(10)
    f["above_200"] = (c > sma(c, 200)).astype(float).where(sma(c, 200).notna())
    f["adx"] = adx(df, 14)
    f["rv20"] = realized_vol(c, 20)
    f["rv_pct"] = f["rv20"].rolling(252, min_periods=60).rank(pct=True)
    f["atr_pct"] = atr(df, 14) / c
    f["vol_ratio"] = df["volume"] / df["volume"].rolling(20, min_periods=20).mean()
    # variance ratio (k=5): <1 suggests mean reversion, >1 trending (Lo & MacKinlay 1988)
    r1 = np.log(c).diff()
    r5 = np.log(c).diff(5)
    f["var_ratio"] = (r5.rolling(100, min_periods=60).var() / (5 * r1.rolling(100, min_periods=60).var()))
    f["zero_vol_frac"] = (df["volume"] == 0).rolling(20, min_periods=5).mean()
    return f


def classify_row(x: pd.Series) -> Regime:
    labels, notes = [], []
    if x.isna().sum() > len(x) / 2:
        return Regime(["UNCERTAIN"], x.to_dict(), ["insufficient history for features"])
    if x.get("zero_vol_frac", 0) > 0.2:
        labels.append("ILLIQUID_ABNORMAL")
    a = x.get("adx", np.nan)
    slope = x.get("ema_slope", np.nan)
    if a >= 25 and slope > 0.01:
        labels.append("STRONG_UPTREND")
    elif a >= 25 and slope < -0.01:
        labels.append("STRONG_DOWNTREND")
    elif a < 20:
        labels.append("SIDEWAYS")
    rvp = x.get("rv_pct", np.nan)
    if rvp >= 0.8:
        labels.append("HIGH_VOLATILITY")
    elif rvp <= 0.2:
        labels.append("LOW_VOLATILITY")
    if x.get("vol_ratio", 0) >= 2 and abs(x.get("ret_20", 0)) > 0.05:
        labels.append("BREAKOUT_CONDITIONS")
    vr = x.get("var_ratio", np.nan)
    if vr < 0.8:
        labels.append("MEAN_REVERTING")
    if ("STRONG_UPTREND" in labels or "STRONG_DOWNTREND" in labels) and "MEAN_REVERTING" in labels:
        notes.append("trend and mean-reversion signals conflict")
        labels.insert(0, "UNCERTAIN_CONFLICTING")
    if not labels:
        labels.append("UNCERTAIN")
    return Regime(labels, {k: (None if pd.isna(v) else round(float(v), 4)) for k, v in x.items()}, notes)


def classify(df: pd.DataFrame) -> Regime:
    f = regime_features(df)
    return classify_row(f.iloc[-1])


def regime_series(df: pd.DataFrame) -> pd.Series:
    f = regime_features(df)
    return f.apply(lambda r: classify_row(r).primary, axis=1)


STRATEGY_REGIME_FIT = {
    # family -> regimes in which the hypothesis is expected to work / fail
    "trend": ({"STRONG_UPTREND", "BREAKOUT_CONDITIONS"}, {"SIDEWAYS", "MEAN_REVERTING", "UNCERTAIN_CONFLICTING"}),
    "mean_reversion": ({"SIDEWAYS", "MEAN_REVERTING", "LOW_VOLATILITY"},
                       {"STRONG_DOWNTREND", "STRONG_UPTREND", "BREAKOUT_CONDITIONS"}),
    "breakout": ({"BREAKOUT_CONDITIONS", "LOW_VOLATILITY", "STRONG_UPTREND"}, {"SIDEWAYS"}),
}


def regime_fit(family: str, regime: Regime) -> tuple[bool, str]:
    good, bad = STRATEGY_REGIME_FIT.get(family, (set(), set()))
    labs = set(regime.labels)
    if "ILLIQUID_ABNORMAL" in labs:
        return False, "illiquid/abnormal conditions"
    if labs & bad:
        return False, f"unfavourable regime {sorted(labs & bad)}"
    if labs & good:
        return True, f"favourable regime {sorted(labs & good)}"
    return False, f"no supporting regime (labels={regime.labels})"
