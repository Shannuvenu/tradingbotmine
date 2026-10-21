"""Machine-learning evaluation against simple baselines, with chronological validation.

Tasks:
  * volatility forecast (next-5-bar realized vol) — baseline: persistence (current 20-bar RV)
  * adverse-move probability (next 5 bars fall > 1.5 ATR) — baseline: training base rate
Every model is registered with features, params, data hash and metrics. A model
is marked `passed_validation` only if it beats the baseline on BOTH validation and
test by a margin; the live engine may then use it ONLY to reduce position size,
never to originate or approve an order.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import brier_score_loss, mean_absolute_error, roc_auc_score

from ..data.validation import data_hash
from .indicators import atr, rsi, volume_ratio

FEATURES = ["rv5", "rv20", "rv60", "absret1", "range_pct", "vol_ratio", "rsi14", "ret20"]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    c = df["close"]
    lr = np.log(c).diff()
    f = pd.DataFrame(index=df.index)
    f["rv5"] = lr.rolling(5).std()
    f["rv20"] = lr.rolling(20).std()
    f["rv60"] = lr.rolling(60).std()
    f["absret1"] = lr.abs()
    f["range_pct"] = (df["high"] - df["low"]) / c
    f["vol_ratio"] = volume_ratio(df["volume"], 20)
    f["rsi14"] = rsi(c, 14) / 100
    f["ret20"] = c.pct_change(20)
    # targets (FUTURE values — only used as labels, never as features)
    f["y_vol"] = lr.rolling(5).std().shift(-5)
    a = atr(df, 14)
    fut_min = df["low"].rolling(5).min().shift(-5)
    f["y_adverse"] = ((c - fut_min) > 1.5 * a).astype(float).where(fut_min.notna())
    return f


def _split(f: pd.DataFrame):
    n = len(f)
    a, b = int(n * 0.6), int(n * 0.8)
    # purge 5 bars at each boundary so label horizons don't overlap the next split
    return f.iloc[:a - 5], f.iloc[a:b - 5], f.iloc[b:]


def evaluate_volatility(df: pd.DataFrame) -> dict:
    f = build_features(df).dropna()
    if len(f) < 300:
        return {"task": "volatility", "status": "insufficient_data", "rows": len(f)}
    tr, va, te = _split(f)
    out = {"task": "volatility_next5", "rows": len(f)}
    models = {"ridge": Ridge(alpha=1.0), "gbr": GradientBoostingRegressor(n_estimators=150, max_depth=2,
                                                                          learning_rate=0.05, random_state=0)}
    for name, m in models.items():
        m.fit(tr[FEATURES], tr["y_vol"])
        out[name] = {"val_mae": float(mean_absolute_error(va["y_vol"], m.predict(va[FEATURES]))),
                     "test_mae": float(mean_absolute_error(te["y_vol"], m.predict(te[FEATURES])))}
    out["baseline_persistence"] = {"val_mae": float(mean_absolute_error(va["y_vol"], va["rv20"])),
                                   "test_mae": float(mean_absolute_error(te["y_vol"], te["rv20"]))}
    best = min(models, key=lambda k: out[k]["val_mae"])
    b = out["baseline_persistence"]
    passed = out[best]["val_mae"] < 0.95 * b["val_mae"] and out[best]["test_mae"] < 0.95 * b["test_mae"]
    out.update({"best_model": best, "passed_validation": bool(passed),
                "decision": f"use {best} for sizing only" if passed else "prefer baseline (persistence)"})
    return out


def evaluate_adverse(df: pd.DataFrame) -> dict:
    f = build_features(df).dropna()
    if len(f) < 300:
        return {"task": "adverse_move", "status": "insufficient_data", "rows": len(f)}
    tr, va, te = _split(f)
    if tr["y_adverse"].nunique() < 2:
        return {"task": "adverse_move", "status": "single_class_in_train"}
    m = LogisticRegression(max_iter=1000, C=0.5)
    m.fit(tr[FEATURES], tr["y_adverse"])
    base = float(tr["y_adverse"].mean())
    res = {"task": "adverse_move_5bar", "rows": len(f), "base_rate_train": round(base, 4)}
    for nm, d in (("val", va), ("test", te)):
        p = m.predict_proba(d[FEATURES])[:, 1]
        y = d["y_adverse"].values
        res[nm] = {"brier_model": float(brier_score_loss(y, p)),
                   "brier_baseline": float(brier_score_loss(y, np.full(len(y), base))),
                   "auc": float(roc_auc_score(y, p)) if len(np.unique(y)) > 1 else None}
        # calibration: predicted vs observed in quintiles
        q = pd.qcut(p, 5, labels=False, duplicates="drop")
        res[nm]["calibration"] = pd.DataFrame({"p": p, "y": y, "q": q}).groupby("q").mean().round(3).to_dict("index")
    passed = all(res[k]["brier_model"] < 0.98 * res[k]["brier_baseline"] for k in ("val", "test"))
    res.update({"passed_validation": bool(passed), "probabilities_calibrated_checked": True,
                "decision": "may reduce size when p is high" if passed else "do not use; baseline is as good"})
    return res


def register(db, task: str, result: dict, df: pd.DataFrame) -> str:
    mid = f"{task}-{uuid.uuid4().hex[:8]}"
    db.execute("INSERT INTO model_registry VALUES (?,?,?,?,?,?,?,?,?)",
               (mid, datetime.now(timezone.utc).isoformat(timespec="seconds"), task, json.dumps(FEATURES),
                json.dumps({k: v for k, v in result.items() if k in ("best_model",)}), data_hash(df),
                json.dumps(result, default=str), json.dumps(result.get("baseline_persistence") or
                                                            {"base_rate": result.get("base_rate_train")}),
                int(bool(result.get("passed_validation")))))
    return mid
