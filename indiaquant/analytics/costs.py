"""Indian transaction-cost model (Upstox, NSE/BSE) — rates as published on
https://upstox.com/brokerage-charges/ (fetched 2026-10-21). Every rate is a
named field so it can be updated in one place; the live engine prefers the
broker's own Brokerage API (GET /v2/charges/brokerage) when authenticated and
falls back to this model in backtests and offline.

Brokerage: delivery ₹20/order; intraday min(₹20, 0.1%); futures min(₹20, 0.05%); options ₹20 flat.
STT (from 1 Apr 2026, Budget 2026-27): delivery 0.1% buy+sell; intraday 0.025% sell; futures 0.05% sell;
  options 0.15% of premium on sell; exercised options 0.15% of intrinsic value.
Exchange txn (NSE, from 1 Mar 2026): equity 0.00307%; futures 0.00183%; options 0.03553% of premium.
  BSE equity varies by scrip group (we use NSE rate as approximation and flag it); BSE options 0.0325%.
SEBI: ₹10/crore. Stamp (buy side): delivery 0.015%, intraday 0.003%, futures 0.002%, options 0.003%.
IPFT: ₹0.01/crore (now merged into transaction charges per Upstox); GST 18% on brokerage+txn(+DP).
DP: ₹20 + GST per scrip per day on delivery sells.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CostRates:
    brokerage_flat: float = 20.0
    brokerage_intraday_pct: float = 0.001
    brokerage_futures_pct: float = 0.0005
    stt_delivery: float = 0.001
    stt_intraday_sell: float = 0.00025
    stt_futures_sell: float = 0.0005
    stt_options_sell_premium: float = 0.0015
    stt_options_exercise: float = 0.0015
    txn_nse_equity: float = 0.0000307
    txn_nse_futures: float = 0.0000183
    txn_nse_options: float = 0.0003553
    txn_bse_options: float = 0.000325
    sebi_per_crore: float = 10.0
    stamp_delivery: float = 0.00015
    stamp_intraday: float = 0.00003
    stamp_futures: float = 0.00002
    stamp_options: float = 0.00003
    ipft_per_crore: float = 0.01
    gst: float = 0.18
    dp_charge: float = 20.0
    source: str = "upstox.com/brokerage-charges (2026-10-21)"


@dataclass
class CostBreakdown:
    brokerage: float = 0.0
    stt: float = 0.0
    exchange: float = 0.0
    sebi: float = 0.0
    stamp: float = 0.0
    gst: float = 0.0
    dp: float = 0.0
    notes: list = field(default_factory=list)

    @property
    def total(self) -> float:
        return round(self.brokerage + self.stt + self.exchange + self.sebi + self.stamp + self.gst + self.dp, 4)

    def as_dict(self) -> dict:
        return {"brokerage": round(self.brokerage, 4), "stt": round(self.stt, 4), "exchange": round(self.exchange, 4),
                "sebi": round(self.sebi, 4), "stamp": round(self.stamp, 4), "gst": round(self.gst, 4),
                "dp": round(self.dp, 4), "total": self.total}


class CostModel:
    """segment: 'EQ_DELIVERY' | 'EQ_INTRADAY' | 'FUT' | 'OPT'."""

    def __init__(self, rates: CostRates | None = None):
        self.r = rates or CostRates()

    def order_cost(self, segment: str, side: str, price: float, qty: float, exchange: str = "NSE") -> CostBreakdown:
        r = self.r
        tv = abs(price * qty)
        c = CostBreakdown()
        buy = side.upper() == "BUY"
        if segment == "EQ_DELIVERY":
            c.brokerage = r.brokerage_flat
            c.stt = tv * r.stt_delivery
            c.exchange = tv * r.txn_nse_equity
            c.stamp = tv * r.stamp_delivery if buy else 0.0
            if not buy:
                c.dp = r.dp_charge * (1 + r.gst)
        elif segment == "EQ_INTRADAY":
            c.brokerage = min(r.brokerage_flat, tv * r.brokerage_intraday_pct)
            c.stt = 0.0 if buy else tv * r.stt_intraday_sell
            c.exchange = tv * r.txn_nse_equity
            c.stamp = tv * r.stamp_intraday if buy else 0.0
        elif segment == "FUT":
            c.brokerage = min(r.brokerage_flat, tv * r.brokerage_futures_pct)
            c.stt = 0.0 if buy else tv * r.stt_futures_sell
            c.exchange = tv * r.txn_nse_futures if exchange == "NSE" else 0.0
            c.stamp = tv * r.stamp_futures if buy else 0.0
        elif segment == "OPT":  # tv = premium turnover
            c.brokerage = r.brokerage_flat
            c.stt = 0.0 if buy else tv * r.stt_options_sell_premium
            c.exchange = tv * (r.txn_nse_options if exchange == "NSE" else r.txn_bse_options)
            c.stamp = tv * r.stamp_options if buy else 0.0
        else:
            raise ValueError(f"unknown segment {segment}")
        if exchange == "BSE" and segment.startswith("EQ"):
            c.notes.append("BSE equity transaction charges vary by scrip group; NSE rate used as approximation")
        c.sebi = tv * r.sebi_per_crore / 1e7
        ipft = tv * r.ipft_per_crore / 1e7
        c.exchange += ipft
        c.gst = (c.brokerage + c.exchange + c.sebi) * r.gst
        return c

    def round_trip(self, segment: str, entry: float, exit_: float, qty: float, long: bool = True,
                   exchange: str = "NSE") -> CostBreakdown:
        a = self.order_cost(segment, "BUY" if long else "SELL", entry, qty, exchange)
        b = self.order_cost(segment, "SELL" if long else "BUY", exit_, qty, exchange)
        out = CostBreakdown()
        for f in ("brokerage", "stt", "exchange", "sebi", "stamp", "gst", "dp"):
            setattr(out, f, getattr(a, f) + getattr(b, f))
        out.notes = a.notes + b.notes
        return out

    def breakeven_move_pct(self, segment: str, price: float, qty: float) -> float:
        """Fractional price move needed just to cover round-trip costs."""
        rt = self.round_trip(segment, price, price, qty).total
        return rt / (price * qty) if price * qty else float("inf")


def segment_for(product: str, is_future: bool = False, is_option: bool = False) -> str:
    if is_option:
        return "OPT"
    if is_future:
        return "FUT"
    return "EQ_INTRADAY" if product == "I" else "EQ_DELIVERY"
