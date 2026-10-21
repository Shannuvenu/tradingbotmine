"""Order lifecycle with duplicate prevention, write-ahead persistence and reconciliation.

Idempotency: each intent maps to a deterministic client tag (prefix + hash of
signal_id + leg). The tag is written to the DB *before* the broker call
(status PENDING_SUBMIT). A second submit with the same tag is refused unless the
earlier one is in a terminal failure state that was confirmed by the broker.

Uncertain outcomes (timeout/5xx) become UNKNOWN. Nothing is retried until
`reconcile_unknown` has queried the broker by tag:
  found  -> adopt broker status
  absent -> NOT_FOUND (still not auto-retried; the next signal cycle may create a new intent)
"""
from __future__ import annotations

import hashlib
import time

from ..broker.upstox import OrderRejected, OrderRequest, OrderStatusUnknown, UpstoxError
from ..logging_setup import get_logger

log = get_logger("orders")

TERMINAL_OK = {"FILLED"}
TERMINAL_FAIL = {"REJECTED", "CANCELLED", "NOT_FOUND"}
ACTIVE = {"PENDING_SUBMIT", "SUBMITTED", "OPEN", "PARTIAL", "UNKNOWN"}


def map_broker_status(st: str, filled: int, qty: int) -> str:
    s = (st or "").lower()
    if s == "complete":
        return "FILLED"
    if s == "rejected":
        return "REJECTED"
    if s == "cancelled":
        return "CANCELLED" if filled == 0 else "PARTIAL_CANCELLED"
    if filled and filled < qty:
        return "PARTIAL"
    return "OPEN"


def make_tag(prefix: str, signal_id: str, leg: str = "E") -> str:
    h = hashlib.sha1(f"{signal_id}:{leg}".encode()).hexdigest()[:12]
    return f"{prefix}{leg}{h}"[:20]


class DuplicateOrder(Exception):
    pass


class OrderManager:
    def __init__(self, client, db, state, tag_prefix: str = "IQ"):
        self.client, self.db, self.state = client, db, state
        self.prefix = tag_prefix
        self.consecutive_failures = 0

    # ------------------------------------------------------------- submit
    def submit(self, req: OrderRequest, signal_id: str, strategy: str, leg: str = "E",
               allow_when_halted: bool = False) -> dict:
        ok, why = self.state.can_place_orders()
        if not ok and not (allow_when_halted and leg in ("X", "K", "S")):
            raise PermissionError(f"order blocked: {why}")
        tag = make_tag(self.prefix, signal_id, leg)
        existing = self.db.get_order(tag)
        if existing and existing["status"] not in ("REJECTED",):
            raise DuplicateOrder(f"tag {tag} already exists with status {existing['status']}")
        req.tag = tag
        rec = {"client_tag": tag, "instrument_key": req.instrument_key, "side": req.side, "quantity": req.quantity,
               "price": req.price, "trigger_price": req.trigger_price, "order_type": req.order_type,
               "product": req.product, "status": "PENDING_SUBMIT", "filled_quantity": 0, "strategy": strategy,
               "signal_id": signal_id}
        self.db.save_order(rec)                       # write-ahead
        self.db.audit("order", f"submit {req.side} {req.quantity} {req.instrument_key} @ {req.price}", rec)
        try:
            ids = self.client.place_order(req)
            rec.update(status="SUBMITTED", broker_order_id=",".join(ids))
            self.consecutive_failures = 0
        except OrderStatusUnknown as e:
            rec.update(status="UNKNOWN", status_message=str(e))
            log.error("order %s outcome unknown: %s", tag, e)
        except OrderRejected as e:
            rec.update(status="REJECTED", status_message=str(e))
            self.consecutive_failures += 1
        except UpstoxError as e:
            rec.update(status="REJECTED", status_message=f"api error: {e}")
            self.consecutive_failures += 1
        self.db.save_order(rec)
        self.db.audit("order", f"result {tag}: {rec['status']}", {"msg": rec.get("status_message")})
        return rec

    # ---------------------------------------------------------- reconcile
    def reconcile_unknown(self) -> list[dict]:
        out = []
        for o in self.db.orders(("UNKNOWN", "PENDING_SUBMIT")):
            try:
                hist = self.client.order_history_by_tag(o["client_tag"])
            except UpstoxError as e:
                log.warning("reconcile %s failed: %s", o["client_tag"], e)
                continue
            if hist:
                last = hist[-1]
                o.update(broker_order_id=last.get("order_id"),
                         status=map_broker_status(last.get("status"), int(last.get("filled_quantity") or 0),
                                                  int(o["quantity"])),
                         filled_quantity=int(last.get("filled_quantity") or 0),
                         average_price=last.get("average_price"), status_message=last.get("status_message"))
            else:
                age = time.time() - _iso_to_epoch(o["created_at"])
                if age > 60:
                    o.update(status="NOT_FOUND", status_message="broker has no order with this tag after 60s")
            self.db.save_order(o)
            out.append(o)
        return out

    def refresh(self) -> list[dict]:
        """Sync local orders with broker order book; returns changed orders."""
        try:
            book = self.client.order_book()
        except UpstoxError as e:
            log.warning("order book refresh failed: %s", e)
            return []
        by_tag = {b.get("tag"): b for b in book if b.get("tag")}
        changed = []
        for o in self.db.orders(tuple(ACTIVE)):
            b = by_tag.get(o["client_tag"])
            if not b:
                continue
            filled = int(b.get("filled_quantity") or 0)
            new = map_broker_status(b.get("status"), filled, int(o["quantity"]))
            if new != o["status"] or filled != (o["filled_quantity"] or 0):
                o.update(status=new, filled_quantity=filled, average_price=b.get("average_price"),
                         broker_order_id=b.get("order_id"), status_message=b.get("status_message"))
                self.db.save_order(o)
                self.db.audit("order", f"{o['client_tag']} -> {new} filled {filled}/{o['quantity']}")
                if new == "REJECTED":
                    self.consecutive_failures += 1
                changed.append(o)
        return changed

    def cancel(self, client_tag: str) -> bool:
        o = self.db.get_order(client_tag)
        if not o or not o.get("broker_order_id") or o["status"] not in ("SUBMITTED", "OPEN", "PARTIAL"):
            return False
        ok = True
        for oid in str(o["broker_order_id"]).split(","):
            try:
                self.client.cancel_order(oid)
            except OrderStatusUnknown:
                ok = False  # will be reconciled by refresh
            except UpstoxError as e:
                log.warning("cancel %s failed: %s", oid, e)
                ok = False
        self.db.audit("order", f"cancel requested {client_tag}", {"ok": ok})
        return ok

    def cancel_all_pending(self) -> int:
        n = 0
        for o in self.db.orders(("SUBMITTED", "OPEN", "PARTIAL")):
            n += int(self.cancel(o["client_tag"]))
        return n

    def cancel_stale_partials(self, max_age_s: int = 120) -> int:
        """Entry orders that are partly filled and stale: cancel remainder; the filled qty becomes the position."""
        n = 0
        for o in self.db.orders(("PARTIAL", "OPEN")):
            if o["client_tag"][len(self.prefix)] != "E":
                continue
            if time.time() - _iso_to_epoch(o["created_at"]) > max_age_s:
                n += int(self.cancel(o["client_tag"]))
        return n

    def active_orders(self) -> list[dict]:
        return self.db.orders(tuple(ACTIVE))


def reconcile_positions(local: dict[str, int], broker_positions: list[dict]) -> list[str]:
    """Compare expected net quantities with broker positions. Returns mismatch descriptions."""
    b = {}
    for p in broker_positions:
        k = p.get("instrument_token") or p.get("instrument_key")
        b[k] = b.get(k, 0) + int(p.get("quantity") or 0)
    issues = []
    for k in set(local) | set(b):
        if int(local.get(k, 0)) != int(b.get(k, 0)):
            issues.append(f"{k}: local {local.get(k, 0)} vs broker {b.get(k, 0)}")
    return issues


def _iso_to_epoch(s: str) -> float:
    from datetime import datetime
    try:
        return datetime.fromisoformat(s).timestamp()
    except (TypeError, ValueError):
        return 0.0
