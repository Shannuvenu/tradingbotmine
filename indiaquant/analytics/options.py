"""Option analytics.

Preferred source of Greeks/IV: the broker (Upstox Option Chain / Option Greeks APIs).
Black-Scholes values computed here are ALWAYS labelled `estimate=True` and record
their inputs (spot, rate, dividend assumption, time-to-expiry convention). NSE
stock/index options are European-style, so Black-Scholes is a reasonable model,
but the risk-free rate and dividend yield are assumptions, not observed data.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from datetime import datetime

from scipy.optimize import brentq
from scipy.stats import norm

from ..data.calendar import IST


@dataclass
class GreeksResult:
    price: float
    delta: float
    gamma: float
    theta_per_day: float
    vega_per_pct: float
    iv: float | None
    estimate: bool
    inputs: dict

    def as_dict(self):
        return asdict(self)


def year_fraction(expiry: str, now: datetime | None = None) -> float:
    now = now or datetime.now(IST)
    exp = datetime.fromisoformat(expiry).replace(hour=15, minute=30, tzinfo=IST)
    secs = (exp - now).total_seconds()
    return max(secs, 0.0) / (365.0 * 24 * 3600)


def bs_price(S, K, T, r, sigma, kind: str, q: float = 0.0) -> float:
    if T <= 0 or sigma <= 0:
        return max(0.0, (S - K) if kind == "CE" else (K - S))
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    if kind == "CE":
        return S * math.exp(-q * T) * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
    return K * math.exp(-r * T) * norm.cdf(-d2) - S * math.exp(-q * T) * norm.cdf(-d1)


def implied_vol(price, S, K, T, r, kind, q=0.0) -> float | None:
    intrinsic = max(0.0, (S - K) if kind == "CE" else (K - S))
    if T <= 0 or price <= intrinsic * math.exp(-r * T) + 1e-9:
        return None
    try:
        return brentq(lambda s: bs_price(S, K, T, r, s, kind, q) - price, 1e-4, 5.0, xtol=1e-6)
    except ValueError:
        return None


def greeks(S, K, T, r, sigma, kind, q=0.0, market_price: float | None = None) -> GreeksResult:
    inputs = {"spot": S, "strike": K, "T_years": round(T, 6), "rate_assumed": r, "div_yield_assumed": q,
              "sigma_input": sigma, "kind": kind, "model": "Black-Scholes (European)"}
    iv = implied_vol(market_price, S, K, T, r, kind, q) if market_price else None
    s = iv or sigma
    if T <= 0 or s <= 0:
        return GreeksResult(bs_price(S, K, T, r, s, kind, q), 0.0, 0.0, 0.0, 0.0, iv, True, inputs)
    d1 = (math.log(S / K) + (r - q + 0.5 * s ** 2) * T) / (s * math.sqrt(T))
    d2 = d1 - s * math.sqrt(T)
    pdf = norm.pdf(d1)
    if kind == "CE":
        delta = math.exp(-q * T) * norm.cdf(d1)
        theta = (-S * pdf * s * math.exp(-q * T) / (2 * math.sqrt(T)) - r * K * math.exp(-r * T) * norm.cdf(d2)
                 + q * S * math.exp(-q * T) * norm.cdf(d1))
    else:
        delta = -math.exp(-q * T) * norm.cdf(-d1)
        theta = (-S * pdf * s * math.exp(-q * T) / (2 * math.sqrt(T)) + r * K * math.exp(-r * T) * norm.cdf(-d2)
                 - q * S * math.exp(-q * T) * norm.cdf(-d1))
    gamma = math.exp(-q * T) * pdf / (S * s * math.sqrt(T))
    vega = S * math.exp(-q * T) * pdf * math.sqrt(T) / 100
    return GreeksResult(bs_price(S, K, T, r, s, kind, q), delta, gamma, theta / 365, vega, iv, True, inputs)


def intrinsic_time_value(S: float, K: float, premium: float, kind: str) -> tuple[float, float]:
    intr = max(0.0, (S - K) if kind == "CE" else (K - S))
    return intr, premium - intr


def chain_to_rows(chain: list[dict]) -> list[dict]:
    """Flatten Upstox /v2/option/chain payload. Broker Greeks are labelled source='broker'."""
    rows = []
    for item in chain:
        for side, kind in (("call_options", "CE"), ("put_options", "PE")):
            o = item.get(side) or {}
            md, g = o.get("market_data") or {}, o.get("option_greeks") or {}
            bid, ask = md.get("bid_price") or 0, md.get("ask_price") or 0
            mid = (bid + ask) / 2 if bid and ask else None
            rows.append({"strike": item.get("strike_price"), "type": kind, "expiry": item.get("expiry"),
                         "instrument_key": o.get("instrument_key"), "ltp": md.get("ltp"), "bid": bid, "ask": ask,
                         "spread_pct": (ask - bid) / mid if mid else None, "oi": md.get("oi"),
                         "volume": md.get("volume"), "iv": g.get("iv"), "delta": g.get("delta"),
                         "gamma": g.get("gamma"), "theta": g.get("theta"), "vega": g.get("vega"),
                         "greeks_source": "broker" if g else "unavailable",
                         "spot": item.get("underlying_spot_price"), "pcr": item.get("pcr")})
    return rows


def long_option_payoff(spot_grid, K, premium, kind, lot):
    """Defined-risk long option payoff at expiry (per lot), excluding costs."""
    import numpy as np
    s = np.asarray(spot_grid, dtype=float)
    intr = np.maximum(s - K, 0) if kind == "CE" else np.maximum(K - s, 0)
    return (intr - premium) * lot


def vertical_spread_payoff(spot_grid, k_long, k_short, prem_long, prem_short, kind, lot):
    """Debit vertical spread (defined risk): long k_long, short k_short of same expiry/type."""
    return long_option_payoff(spot_grid, k_long, prem_long, kind, lot) - long_option_payoff(
        spot_grid, k_short, prem_short, kind, lot)
