"""Trading engine: signal → research gate → regime gate → STOCKSHIELD gate → risk engine → order.

Runs in ANALYSIS mode (signals + decisions logged, no orders) unless the
execution state is LIVE_ACTIVE for today. Deterministic rules only; no ML or
LLM output can originate or approve an order.

Research gate: a strategy may trade an instrument live ONLY if its most recent
evaluation on REAL data (not synthetic) for that instrument has verdict
CANDIDATE. With no such evidence the engine's answer is NO TRADE.
"""
from __future__ import annotations

import json
import time
import uuid

import pandas as pd

from ..analytics import regime as regime_mod
from ..analytics import stockshield
from ..broker.upstox import OrderRequest, UpstoxError
from ..data.calendar import now_ist, parse_hhmm, to_ist
from ..data.feed import LiveFeed
from ..data.instruments import InstrumentMaster, round_to_tick
from ..logging_setup import get_logger
from ..strategies.catalog import REGISTRY
from .orders import OrderManager, reconcile_positions
from .risk import AccountSnapshot, OrderIntent, RiskEngine

log = get_logger("engine")


def approved_strategies(db, key: str) -> set[str]:
    rows = db.query("SELECT strategy, metrics, data_source, ts FROM backtest_runs WHERE instrument_key=? "
                    "ORDER BY ts", (key,))
    latest = {}
    for r in rows:
        if str(r["data_source"]).startswith("SYNTHETIC"):
            continue
        latest[r["strategy"]] = r
    out = set()
    for name, r in latest.items():
        try:
            m = json.loads(r["metrics"])
        except (TypeError, ValueError):
            continue
        if m.get("verdict") == "CANDIDATE":
            out.add(name)
    return out


class TradingEngine:
    def __init__(self, settings, db, client, state, calendar, feed: LiveFeed | None = None):
        self.S, self.db, self.client, self.state, self.cal = settings, db, client, state, calendar
        self.instruments = InstrumentMaster(db)
        self.risk = RiskEngine(settings.risk, calendar=calendar)
        self.om = OrderManager(client, db, state, settings.order_tag_prefix)
        self.feed = feed
        self.profile: dict = {}
        self.last_cycle: dict = {}

    # ------------------------------------------------------------ account
    def snapshot(self) -> AccountSnapshot:
        cash = self.client.available_cash()
        positions = []
        for p in self.client.positions():
            positions.append({"instrument_key": p.get("instrument_token"), "quantity": int(p.get("quantity") or 0),
                              "value": float(p.get("last_price") or 0) * int(p.get("quantity") or 0),
                              "realised": float(p.get("realised") or 0), "unrealised": float(p.get("unrealised") or 0),
                              "product": p.get("product"), "average_price": p.get("average_price")})
        today = now_ist().date().isoformat()
        open_orders = [{"instrument_key": o["instrument_key"], "side": o["side"], "quantity": o["quantity"],
                        "price": o["price"]} for o in self.om.active_orders()]
        n_today = len(self.db.orders(since=today))
        return AccountSnapshot(available_cash=cash, positions=[p for p in positions if p["quantity"] != 0],
                               open_orders=open_orders,
                               realized_pnl_today=sum(p["realised"] for p in positions),
                               unrealized_pnl_today=sum(p["unrealised"] for p in positions),
                               orders_today=n_today, consecutive_failures=self.om.consecutive_failures,
                               segments_enabled=tuple(self.profile.get("exchanges") or ()),
                               products_enabled=tuple(self.profile.get("products") or ()))

    # ------------------------------------------------------------ signals
    def _intraday_bars(self, key: str) -> pd.DataFrame:
        df = self.client.intraday(key, "minutes", 1)
        # drop the still-forming current minute: only completed bars generate signals
        if len(df):
            cutoff = pd.Timestamp(now_ist()).floor("min")
            df = df[[to_ist(t) < cutoff.to_pydatetime() for t in df.index]]
        prev = self.db.load_candles(key, "1m")
        if len(prev):
            prev = prev[prev.index.date < now_ist().date()].tail(375 * 2)
            df = pd.concat([prev[["open", "high", "low", "close", "volume", "oi"]], df]).sort_index()
            df = df[~df.index.duplicated(keep="last")]
        return df

    def scan(self, key: str) -> list[dict]:
        """Evaluate every enabled strategy on `key`; returns decision records (also persisted)."""
        out = []
        daily = self.db.load_candles(key, "1d")
        approved = approved_strategies(self.db, key)
        reg = regime_mod.classify(daily) if len(daily) >= 60 else None
        shield = stockshield.analyze(daily) if len(daily) >= 40 else None
        intraday = None
        for name in self.S.enabled_strategies:
            strat = REGISTRY.get(name)
            if strat is None:
                continue
            if strat.style == "intraday":
                if intraday is None:
                    try:
                        intraday = self._intraday_bars(key)
                    except UpstoxError as e:
                        log.warning("intraday bars %s: %s", key, e)
                        intraday = pd.DataFrame()
                df = intraday
            else:
                df = daily
            if df is None or len(df) < 30:
                continue
            ctx = {}
            if strat.needs_benchmark:
                ctx["benchmark"] = self.db.load_candles(self.S.benchmark_key, "1d")
            sig = strat.latest_signal(df, key, None, ctx)
            if sig is None:
                continue
            reasons = []
            if name not in approved:
                reasons.append("research gate: no CANDIDATE verdict on real data for this instrument")
            if reg is not None:
                fit, why = regime_mod.regime_fit(strat.family, reg)
                if not fit:
                    reasons.append(f"regime gate: {why}")
            if shield is not None and shield.level == "HIGH":
                reasons.append(f"STOCKSHIELD risk HIGH (score {shield.score})")
            rec = {"signal_id": f"{name}:{key}:{sig.bar_ts}", "ts": now_ist().isoformat(), "instrument_key": key,
                   "strategy": name, "side": sig.side, "entry": sig.entry_ref, "stop": sig.stop, "target": sig.target,
                   "style": sig.style, "data_ts": sig.bar_ts, "explanation": sig.explanation,
                   "decision": "NO_TRADE" if reasons else "PASS_TO_RISK", "decision_reasons": reasons}
            self.db.save_signal(rec)
            out.append(rec)
        return out

    # ------------------------------------------------------------ actions
    def _try_enter(self, rec: dict, acct: AccountSnapshot):
        ins = self.instruments.get(rec["instrument_key"])
        q = self.feed.book.get(rec["instrument_key"]) if self.feed else None
        product = "I" if rec["style"] == "intraday" else "D"
        bar_close_epoch = pd.Timestamp(rec["data_ts"]).timestamp() + (60 if product == "I" else 0)
        intent = OrderIntent(rec["instrument_key"], "BUY", rec["entry"], rec["stop"], rec["target"], product,
                             rec["strategy"], rec["signal_id"], bar_close_epoch)
        d = self.risk.check(intent, ins, q, acct)
        rec["decision"] = "APPROVED" if d.approved else "RISK_REJECTED"
        rec["decision_reasons"] = d.reasons or [f"qty {d.quantity} @ {d.limit_price}, est costs ₹{d.est_costs:.2f}"]
        self.db.save_signal(rec)
        if not d.approved:
            return None
        ok, why = self.state.can_place_orders()
        if not ok:
            rec["decision"] = "APPROVED_NOT_SENT"
            rec["decision_reasons"].append(why)
            self.db.save_signal(rec)
            return None
        req = OrderRequest(rec["instrument_key"], "BUY", d.quantity, d.limit_price, "LIMIT", product)
        res = self.om.submit(req, rec["signal_id"], rec["strategy"], leg="E")
        meta = self.db.get_state("pos_meta", {})
        meta[rec["instrument_key"]] = {"entry_tag": res["client_tag"], "stop": rec["stop"], "target": rec["target"],
                                       "product": product, "strategy": rec["strategy"], "signal_id": rec["signal_id"],
                                       "sl_tag": None}
        self.db.set_state("pos_meta", meta)
        return res

    def _protect(self, acct: AccountSnapshot):
        """Place a stop-loss (SL limit) order for any filled position that lacks one."""
        meta = self.db.get_state("pos_meta", {})
        for p in acct.positions:
            m = meta.get(p["instrument_key"])
            if not m or m.get("sl_tag") or p["quantity"] <= 0:
                continue
            ins = self.instruments.get(p["instrument_key"])
            trig = round_to_tick(m["stop"], ins.tick_size, "down")
            limit = round_to_tick(trig * (1 - 0.01), ins.tick_size, "down")
            req = OrderRequest(p["instrument_key"], "SELL", p["quantity"], limit, "SL", m["product"],
                               trigger_price=trig)
            try:
                res = self.om.submit(req, m["signal_id"], m["strategy"], leg="S", allow_when_halted=True)
                m["sl_tag"] = res["client_tag"]
            except Exception as e:
                log.error("could not place protective stop for %s: %s", p["instrument_key"], e)
                self.state.halt(f"protective stop failed for {p['instrument_key']}: {e}")
        self.db.set_state("pos_meta", meta)

    def exit_position(self, key: str, qty: int, reason: str, allow_when_halted: bool = True):
        meta = self.db.get_state("pos_meta", {}).get(key, {})
        if meta.get("sl_tag"):
            self.om.cancel(meta["sl_tag"])
        q = self.feed.book.get(key) if self.feed else None
        ins = self.instruments.get(key)
        acct = self.snapshot()
        d = self.risk.check(OrderIntent(key, "SELL", 0, 0, None, meta.get("product", "I"), "exit",
                                        f"exit:{key}:{reason}:{int(time.time() // 60)}", time.time(), is_exit=True,
                                        quantity=qty), ins, q, acct)
        if not d.approved:
            log.error("exit for %s blocked: %s", key, d.reasons)
            self.db.audit("exit", f"exit blocked {key}", {"reasons": d.reasons})
            return None
        req = OrderRequest(key, "SELL", qty, d.limit_price, "LIMIT", meta.get("product", "I"))
        return self.om.submit(req, f"exit:{key}:{reason}:{uuid.uuid4().hex[:6]}", "exit", leg="X",
                              allow_when_halted=allow_when_halted)

    def flatten_all(self, reason: str) -> list:
        """EMERGENCY LIQUIDATION (explicit action only). Sends marketable LIMIT sells for every long position.
        Consequences: crosses the spread, may fill partially or not at all in a fast market, incurs charges,
        and realises P&L. Cancelling orders alone does NOT close positions."""
        out = []
        for p in self.snapshot().positions:
            if p["quantity"] > 0:
                out.append(self.exit_position(p["instrument_key"], p["quantity"], f"flatten:{reason}"))
        self.db.audit("kill", "flatten_all executed", {"reason": reason, "orders": len(out)})
        return out

    def kill_switch(self, reason: str, flatten: bool = False) -> dict:
        self.state.halt(f"KILL SWITCH: {reason}")
        n = self.om.cancel_all_pending()
        res = {"halted": True, "cancel_requests": n, "flattened": None}
        if flatten:
            res["flattened"] = len(self.flatten_all(reason))
        self.db.audit("kill", "kill switch", res)
        return res

    # --------------------------------------------------------------- cycle
    def cycle(self) -> dict:
        info = {"ts": now_ist().isoformat(), "state": self.state.state}
        try:
            if not self.profile:
                self.profile = self.client.profile()
            self.om.reconcile_unknown()
            self.om.refresh()
            self.om.cancel_stale_partials()
            acct = self.snapshot()
        except UpstoxError as e:
            info["error"] = str(e)
            if self.om.consecutive_failures + self.client.consecutive_errors >= self.S.risk.max_consecutive_failures:
                self.state.halt(f"consecutive API failures: {e}")
            self.last_cycle = info
            return info
        if self.risk.daily_loss_breached(acct) and self.state.state != "HALTED":
            self.kill_switch("daily loss limit reached", flatten=False)
        # broker vs local reconciliation (positions we opened)
        meta = self.db.get_state("pos_meta", {})
        expected = {}
        for k, m in meta.items():
            o = self.db.get_order(m["entry_tag"])
            if o:
                expected[k] = int(o.get("filled_quantity") or 0)
        mism = reconcile_positions({k: v for k, v in expected.items() if v},
                                   [p for p in self.client.positions() if p.get("instrument_token") in expected])
        info["reconciliation_issues"] = mism
        # protective stops & intraday square-off
        self._protect(acct)
        if now_ist().time() >= parse_hhmm(self.S.risk.intraday_squareoff_time):
            for p in acct.positions:
                if meta.get(p["instrument_key"], {}).get("product") == "I" and p["quantity"] > 0:
                    self.exit_position(p["instrument_key"], p["quantity"], "squareoff")
        # new signals
        st = self.cal.status()
        info["session"] = st.phase
        decisions = []
        if st.is_open:
            for key in self.S.watchlist:
                try:
                    for rec in self.scan(key):
                        if rec["decision"] == "PASS_TO_RISK":
                            self._try_enter(rec, acct)
                            acct = self.snapshot()
                        decisions.append({k: rec[k] for k in ("strategy", "instrument_key", "decision")})
                except Exception as e:
                    log.exception("scan %s failed: %s", key, e)
        info["decisions"] = decisions
        self.last_cycle = info
        self.db.set_state("last_cycle", info)
        return info

    def run(self, interval_s: int = 60, max_cycles: int | None = None):
        n = 0
        if self.feed:
            self.feed.start()
        try:
            while max_cycles is None or n < max_cycles:
                self.cycle()
                n += 1
                time.sleep(interval_s)
        except KeyboardInterrupt:
            log.warning("engine stopped by user (Ctrl+C). Open orders/positions are NOT auto-closed.")
        finally:
            if self.feed:
                self.feed.stop()
