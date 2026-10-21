"""Pre-trade risk engine for a small cash account.

Every check returns a reason; ANY failure rejects the order. The engine never
loosens a limit, never switches instrument, and never scales a trade up to
"make it fit". If one share/lot is unaffordable, the answer is NO TRADE.

Modelled risk is not maximum loss: gaps, partial fills, rejections and
charges can exceed the stop distance. Daily-loss and consecutive-failure
halts exist for that reason.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field

from ..analytics.costs import CostModel, segment_for
from ..config import RiskLimits
from ..data.calendar import now_ist, parse_hhmm
from ..data.instruments import Instrument, is_valid_tick, round_to_tick


@dataclass
class AccountSnapshot:
    available_cash: float
    positions: list = field(default_factory=list)       # [{instrument_key, quantity, value, pnl}]
    open_orders: list = field(default_factory=list)     # [{instrument_key, side, quantity, price}]
    realized_pnl_today: float = 0.0
    unrealized_pnl_today: float = 0.0
    orders_today: int = 0
    consecutive_failures: int = 0
    as_of: float = field(default_factory=time.time)
    segments_enabled: tuple = ()                        # from profile.exchanges, e.g. ('NSE','BSE','NFO')
    products_enabled: tuple = ()                        # from profile.products


@dataclass
class OrderIntent:
    instrument_key: str
    side: str
    entry_price: float
    stop_price: float
    target_price: float | None
    product: str
    strategy: str
    signal_id: str
    signal_ts: float                # epoch seconds of the bar/quote that produced the signal
    is_exit: bool = False
    quantity: int | None = None     # exits specify qty; entries are sized here


@dataclass
class RiskDecision:
    approved: bool
    quantity: int = 0
    limit_price: float = 0.0
    reasons: list = field(default_factory=list)
    checks: dict = field(default_factory=dict)
    est_costs: float = 0.0
    modelled_risk: float = 0.0

    def fail(self, name: str, why: str):
        self.checks[name] = f"FAIL: {why}"
        self.reasons.append(f"{name}: {why}")
        self.approved = False

    def ok(self, name: str, detail: str = ""):
        self.checks[name] = f"ok {detail}".strip()


class RiskEngine:
    def __init__(self, limits: RiskLimits, costs: CostModel | None = None, calendar=None):
        self.L = limits
        self.costs = costs or CostModel()
        self.calendar = calendar
        self.time_fn = lambda: now_ist().time()   # injectable for tests

    def daily_loss_breached(self, acct: AccountSnapshot) -> bool:
        loss = acct.realized_pnl_today + acct.unrealized_pnl_today
        return loss <= -self.L.max_daily_loss_pct * self.L.starting_capital

    def check(self, intent: OrderIntent, ins: Instrument | None, quote, acct: AccountSnapshot,
              now: float | None = None) -> RiskDecision:
        L = self.L
        now = now or time.time()
        d = RiskDecision(approved=True)
        if ins is None:
            d.fail("instrument", f"{intent.instrument_key} not in instrument master")
            return d
        # --- segment / product / regulatory restrictions
        if ins.is_derivative and not L.allow_derivatives and not intent.is_exit:
            d.fail("segment", "derivatives disabled by configuration (allow_derivatives=false)")
        if ins.is_option and not intent.is_exit:
            if intent.side == "SELL":
                d.fail("option_writing", "option writing (unlimited/undefined risk) is not supported")
            elif not L.allow_option_buying:
                d.fail("option_buying", "option buying disabled (allow_option_buying=false)")
        if intent.product not in L.allowed_products:
            d.fail("product", f"product {intent.product} not in allowed {L.allowed_products}")
        if acct.products_enabled and intent.product not in acct.products_enabled:
            d.fail("broker_product", f"product {intent.product} not enabled on account {acct.products_enabled}")
        exch_needed = ("NFO" if ins.segment == "NSE_FO" else "BFO" if ins.segment == "BSE_FO" else ins.exchange)
        if acct.segments_enabled and exch_needed not in acct.segments_enabled:
            d.fail("broker_segment", f"{exch_needed} not enabled on account {acct.segments_enabled}")
        if intent.side == "SELL" and not intent.is_exit and not L.allow_short:
            d.fail("short", "short selling disabled (allow_short=false)")
        else:
            d.ok("direction")
        # --- session
        if self.calendar is not None:
            st = self.calendar.status(exchange=ins.exchange)
            if not st.is_open:
                d.fail("session", f"{st.phase}: {st.detail}")
            else:
                d.ok("session")
        t = self.time_fn()
        if not intent.is_exit and intent.product == "I" and t > parse_hhmm(L.intraday_entry_cutoff):
            d.fail("entry_cutoff", f"no new intraday entries after {L.intraday_entry_cutoff}")
        # --- data freshness
        if quote is None:
            d.fail("quote", "no live quote")
            return d
        age = now - quote.recv_ts
        if age > L.max_data_age_seconds:
            d.fail("stale_quote", f"quote age {age:.0f}s > {L.max_data_age_seconds}s")
        sig_age = now - intent.signal_ts
        max_sig_age = 120 if intent.product == "I" else 96 * 3600  # swing: bar close may be before a weekend
        if not intent.is_exit and sig_age > max_sig_age:
            d.fail("stale_signal", f"signal age {sig_age:.0f}s > {max_sig_age}s")
        # --- spread / liquidity
        sp = quote.spread_pct
        if sp is None:
            if not intent.is_exit:
                d.fail("spread", "no bid/ask available to measure spread")
        elif sp > L.max_spread_pct:
            d.fail("spread", f"spread {sp:.3%} > {L.max_spread_pct:.3%}")
        else:
            d.ok("spread", f"{sp:.3%}")
        # --- price: marketable LIMIT with buffer, on tick grid (MARKET orders not allowed by API)
        ref = (quote.ask if intent.side == "BUY" else quote.bid) or quote.ltp
        if not ref or ref <= 0:
            d.fail("price", "no valid reference price")
            return d
        raw = ref * (1 + L.limit_price_buffer_pct) if intent.side == "BUY" else ref * (1 - L.limit_price_buffer_pct)
        limit = round_to_tick(raw, ins.tick_size, "up" if intent.side == "BUY" else "down")
        if not is_valid_tick(limit, ins.tick_size):
            d.fail("tick", f"price {limit} not on tick {ins.tick_size}")
        d.limit_price = limit
        # --- exits: quantity given; only verify it does not exceed the held position
        if intent.is_exit:
            held = sum(int(p.get("quantity", 0)) for p in acct.positions
                       if p.get("instrument_key") == intent.instrument_key)
            q = int(intent.quantity or 0)
            if q <= 0 or (intent.side == "SELL" and q > held):
                d.fail("exit_qty", f"exit qty {q} exceeds held {held}")
            d.quantity = q
            d.approved = d.approved and not d.reasons
            return d
        # --- sizing from risk (stop distance) and exposure; integer lots
        stop = intent.stop_price
        if not stop or stop >= limit:
            d.fail("stop", f"invalid stop {stop} for long entry at {limit}")
            return d
        risk_ps = limit - stop
        lot = max(int(ins.lot_size or 1), 1)
        unit_cost = limit  # cash product: full value (no leverage)
        capital = min(acct.available_cash, L.starting_capital if L.starting_capital > 0 else acct.available_cash)
        exposure_now = sum(abs(float(p.get("value") or 0)) for p in acct.positions)
        pending_notional = sum(float(o.get("price", 0)) * int(o.get("quantity", 0)) for o in acct.open_orders
                               if o.get("side") == "BUY")
        room = max(0.0, capital * L.max_capital_exposure_pct - exposure_now - pending_notional)
        q_risk = math.floor(capital * L.max_risk_per_trade_pct / (risk_ps * lot)) * lot
        q_room = math.floor(room / (unit_cost * lot)) * lot
        q_notional = math.floor(L.max_order_notional / (unit_cost * lot)) * lot
        q_conc = math.floor(capital * L.max_concentration_pct / (unit_cost * lot)) * lot
        qty = max(0, min(q_risk, q_room, q_notional, q_conc))
        d.checks["sizing"] = (f"risk-cap {q_risk}, exposure-room {q_room}, notional-cap {q_notional}, "
                              f"concentration-cap {q_conc} -> {qty}")
        if qty < lot:
            d.fail("affordability", f"cannot size even 1 {'lot' if lot > 1 else 'share'} "
                                    f"(price ₹{limit:,.2f} × lot {lot}, stop distance ₹{risk_ps:.2f}, cash ₹{acct.available_cash:,.2f})")
            return d
        if ins.freeze_quantity and qty > ins.freeze_quantity:
            d.fail("freeze_qty", f"qty {qty} > exchange freeze qty {ins.freeze_quantity}")
        notional = qty * unit_cost
        if notional > acct.available_cash:
            d.fail("funds", f"notional ₹{notional:,.2f} > available ₹{acct.available_cash:,.2f}")
        # --- costs vs risk/reward
        seg = segment_for(intent.product, ins.instrument_type == "FUT", ins.is_option)
        exit_ref = intent.target_price or (limit + 2 * risk_ps)
        rt = self.costs.round_trip(seg, limit, exit_ref, qty, True, ins.exchange)
        d.est_costs = rt.total
        d.modelled_risk = risk_ps * qty + rt.total
        if notional + self.costs.order_cost(seg, "BUY", limit, qty, ins.exchange).total > acct.available_cash:
            d.fail("funds_incl_costs", "notional plus entry charges exceeds available cash")
        if rt.total > L.max_cost_to_risk_ratio * risk_ps * qty:
            d.fail("costs", f"round-trip costs ₹{rt.total:.2f} > {L.max_cost_to_risk_ratio:.0%} of stop risk "
                            f"₹{risk_ps * qty:.2f}")
        reward = (exit_ref - limit) * qty
        if reward < L.min_reward_cost_ratio * rt.total:
            d.fail("reward_vs_costs", f"expected move ₹{reward:.2f} < {L.min_reward_cost_ratio}× costs ₹{rt.total:.2f}")
        # --- portfolio limits
        open_pos = {p["instrument_key"] for p in acct.positions if int(p.get("quantity", 0)) != 0}
        if intent.instrument_key in open_pos:
            d.fail("existing_position", "already holding this instrument")
        if any(o.get("instrument_key") == intent.instrument_key for o in acct.open_orders):
            d.fail("pending_order", "an order for this instrument is already pending")
        if len(open_pos) >= L.max_open_positions:
            d.fail("max_positions", f"{len(open_pos)} open >= {L.max_open_positions}")
        if acct.orders_today >= L.max_orders_per_session:
            d.fail("max_orders", f"{acct.orders_today} orders today >= {L.max_orders_per_session}")
        if acct.consecutive_failures >= L.max_consecutive_failures:
            d.fail("failures", f"{acct.consecutive_failures} consecutive failures")
        if self.daily_loss_breached(acct):
            d.fail("daily_loss", "daily loss limit reached")
        d.quantity = qty
        d.approved = not d.reasons
        return d
