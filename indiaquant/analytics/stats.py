"""Statistical tools: ADF test and Engle-Granger cointegration (no statsmodels dependency).

ADF critical values: MacKinnon (2010) asymptotic approximations for the
constant-only case. For cointegration residuals (2 variables) we use the
MacKinnon (2010) Engle-Granger critical values, which are stricter than ADF.
These are asymptotic; small samples make the test less reliable.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

ADF_CRIT_C = {"1%": -3.43, "5%": -2.86, "10%": -2.57}
EG_CRIT_2 = {"1%": -3.90, "5%": -3.34, "10%": -3.04}


def adf_stat(y: np.ndarray, lags: int = 1) -> float:
    y = np.asarray(y, dtype=float)
    dy = np.diff(y)
    n = len(dy) - lags
    if n < 20:
        return float("nan")
    X = [y[lags:-1], np.ones(n)]
    for i in range(1, lags + 1):
        X.append(dy[lags - i:-i])
    X = np.column_stack(X)
    Y = dy[lags:]
    beta, *_ = np.linalg.lstsq(X, Y, rcond=None)
    resid = Y - X @ beta
    s2 = resid @ resid / (n - X.shape[1])
    cov = s2 * np.linalg.inv(X.T @ X)
    return float(beta[0] / np.sqrt(cov[0, 0]))


def engle_granger(a: pd.Series, b: pd.Series, lags: int = 1) -> dict:
    df = pd.concat([np.log(a), np.log(b)], axis=1).dropna()
    if len(df) < 60:
        return {"cointegrated": False, "reason": "fewer than 60 overlapping observations"}
    y, x = df.iloc[:, 0].values, df.iloc[:, 1].values
    X = np.column_stack([x, np.ones(len(x))])
    (beta, alpha), *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - (beta * x + alpha)
    t = adf_stat(resid, lags)
    half_life = None
    dr = np.diff(resid)
    k = np.polyfit(resid[:-1], dr, 1)[0]
    if k < 0:
        half_life = float(-np.log(2) / k)
    return {"t_stat": round(t, 3), "crit": EG_CRIT_2, "cointegrated": bool(t < EG_CRIT_2["5%"]),
            "hedge_ratio": float(beta), "alpha": float(alpha), "half_life_bars": half_life, "n": len(df)}


def sharpe(returns: pd.Series, periods: int = 252) -> float:
    r = returns.dropna()
    if len(r) < 2 or r.std() == 0:
        return float("nan")
    return float(r.mean() / r.std() * np.sqrt(periods))


def sortino(returns: pd.Series, periods: int = 252) -> float:
    r = returns.dropna()
    dd = r[r < 0]
    if len(r) < 2 or len(dd) < 2 or dd.std() == 0:
        return float("nan")
    return float(r.mean() / np.sqrt((dd ** 2).mean()) * np.sqrt(periods))


def bootstrap_mean_ci(x: np.ndarray, n: int = 2000, alpha: float = 0.05, seed: int = 0) -> tuple[float, float]:
    x = np.asarray(x, dtype=float)
    if len(x) < 5:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    means = rng.choice(x, size=(n, len(x)), replace=True).mean(axis=1)
    return float(np.quantile(means, alpha / 2)), float(np.quantile(means, 1 - alpha / 2))
