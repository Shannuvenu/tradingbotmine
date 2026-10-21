"""TEST DOUBLES ONLY. A fake broker that records calls and never touches the network."""
from __future__ import annotations

import time

from indiaquant.broker.upstox import OrderRejected, OrderStatusUnknown
from indiaquant.data.feed import Quote
from indiaquant.data.instruments import Instrument


def eq_instrument(key="NSE_EQ|INE154A01025", sym="ITC", tick=0.05, lot=1):
    return Instrument(key, "NSE", "NSE_EQ", "EQ", sym, sym, key.split("|")[1], "1660", lot, tick, 100000.0)


def quote(key="NSE_EQ|INE154A01025", ltp=400.0, bid=399.9, ask=400.1, age=0.0):
    now = time.time()
    return Quote(key, ltp, now - age, now - age, 1e6, bid, ask, 100, 100, "test")


class FakeClient:
    def __init__(self):
        self.placed, self.cancelled = [], []
        self.mode = "ok"            # ok | timeout | reject
        self.book, self.history = [], {}
        self._positions = []
        self.cash = 1000.0
        self.consecutive_errors = 0
        self._token = "TEST"

    @property
    def has_token(self):
        return True

    def place_order(self, req):
        self.placed.append(req)
        if self.mode == "timeout":
            raise OrderStatusUnknown("timeout", 0, endpoint="place_v3")
        if self.mode == "reject":
            raise OrderRejected("insufficient funds", 400, endpoint="place_v3")
        oid = f"OID{len(self.placed)}"
        self.book.append({"order_id": oid, "tag": req.tag, "status": "open", "filled_quantity": 0,
                          "quantity": req.quantity, "average_price": 0})
        return [oid]

    def cancel_order(self, oid):
        self.cancelled.append(oid)
        for b in self.book:
            if b["order_id"] == oid:
                b["status"] = "cancelled"
        return {"status": "success"}

    def order_book(self):
        return self.book

    def order_history_by_tag(self, tag):
        return self.history.get(tag, [])

    def positions(self):
        return self._positions

    def available_cash(self):
        return self.cash

    def profile(self):
        return {"exchanges": ["NSE", "BSE"], "products": ["I", "D"], "is_active": True}
