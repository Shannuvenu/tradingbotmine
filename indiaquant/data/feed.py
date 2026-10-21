"""Live market data: WebSocket (Upstox Market Data Feed V3 via official SDK) with
REST-polling fallback, de-duplication, out-of-order rejection and freshness checks.

The V3 WebSocket sends protobuf frames; decoding is delegated to the official
`upstox-python-sdk` MarketDataStreamerV3 (pip install upstox-python-sdk). If the
SDK is missing or the socket drops, `LiveFeed` falls back to polling the
Full Market Quote REST API (rate-limited) so the engine never trades on a dead
stream: every quote carries a receive timestamp, and stale quotes are rejected
by the risk engine (max_data_age_seconds).
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

from ..logging_setup import get_logger

log = get_logger("feed")


@dataclass
class Quote:
    key: str
    ltp: float
    exchange_ts: float          # epoch seconds from exchange/broker (0 if unknown)
    recv_ts: float              # epoch seconds when we received it
    volume: float = 0.0
    bid: float | None = None
    ask: float | None = None
    bid_qty: float | None = None
    ask_qty: float | None = None
    source: str = ""

    @property
    def spread_pct(self) -> float | None:
        if self.bid and self.ask and self.ask >= self.bid > 0:
            return (self.ask - self.bid) / ((self.ask + self.bid) / 2)
        return None

    @property
    def mid(self) -> float:
        if self.bid and self.ask and self.ask >= self.bid > 0:
            return (self.bid + self.ask) / 2
        return self.ltp


@dataclass
class QuoteBook:
    quotes: dict[str, Quote] = field(default_factory=dict)
    seen: dict[str, tuple] = field(default_factory=dict)
    dropped_dup: int = 0
    dropped_old: int = 0
    lock: threading.Lock = field(default_factory=threading.Lock)

    def update(self, q: Quote) -> bool:
        """Returns True if accepted. Rejects exact duplicates and out-of-order events."""
        sig = (q.exchange_ts, q.ltp, q.volume, q.bid, q.ask)
        with self.lock:
            if self.seen.get(q.key) == sig:
                self.dropped_dup += 1
                return False
            cur = self.quotes.get(q.key)
            if cur and q.exchange_ts and cur.exchange_ts and q.exchange_ts < cur.exchange_ts:
                self.dropped_old += 1
                return False
            self.quotes[q.key] = q
            self.seen[q.key] = sig
            return True

    def get(self, key: str, max_age: float | None = None, now: float | None = None) -> Quote | None:
        q = self.quotes.get(key)
        if q is None:
            return None
        if max_age is not None:
            now = now or time.time()
            if now - q.recv_ts > max_age:
                return None
        return q

    def age(self, key: str) -> float | None:
        q = self.quotes.get(key)
        return None if q is None else time.time() - q.recv_ts


def quote_from_rest(key: str, v: dict, now: float | None = None) -> Quote:
    """Parse Upstox full-market-quote item (v2 /market-quote/quotes)."""
    now = now or time.time()
    depth = v.get("depth") or {}
    buy = (depth.get("buy") or [{}])[0]
    sell = (depth.get("sell") or [{}])[0]
    ts = v.get("last_trade_time") or v.get("timestamp") or 0
    try:
        ts = float(ts) / (1000.0 if float(ts) > 1e11 else 1.0)
    except (TypeError, ValueError):
        ts = 0.0
    return Quote(key=key, ltp=float(v.get("last_price") or 0), exchange_ts=ts, recv_ts=now,
                 volume=float(v.get("volume") or 0), bid=buy.get("price") or None, ask=sell.get("price") or None,
                 bid_qty=buy.get("quantity"), ask_qty=sell.get("quantity"), source="rest")


class LiveFeed:
    def __init__(self, client, keys: list[str], poll_seconds: float = 3.0, use_websocket: bool = True):
        self.client = client
        self.keys = list(dict.fromkeys(keys))
        self.book = QuoteBook()
        self.poll_seconds = poll_seconds
        self.use_websocket = use_websocket
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.mode = "stopped"
        self.last_error = ""
        self._streamer = None

    # ----------------------------------------------------------- websocket
    def _start_ws(self) -> bool:
        try:
            import upstox_client  # official SDK
        except ImportError:
            self.last_error = "upstox-python-sdk not installed; using REST polling"
            return False
        try:
            conf = upstox_client.Configuration()
            conf.access_token = self.client._token
            streamer = upstox_client.MarketDataStreamerV3(upstox_client.ApiClient(conf), self.keys, "full")

            def on_message(msg):
                now = time.time()
                for k, feed in (msg.get("feeds") or {}).items():
                    ff = feed.get("fullFeed") or {}
                    mf = ff.get("marketFF") or ff.get("indexFF") or {}
                    ltpc = mf.get("ltpc") or feed.get("ltpc") or {}
                    lvl = ((mf.get("marketLevel") or {}).get("bidAskQuote") or [{}])[0]
                    ts = float(ltpc.get("ltt") or 0) / 1000.0
                    self.book.update(Quote(key=k, ltp=float(ltpc.get("ltp") or 0), exchange_ts=ts, recv_ts=now,
                                           volume=float(mf.get("vtt") or 0), bid=lvl.get("bidP"),
                                           ask=lvl.get("askP"), bid_qty=lvl.get("bidQ"), ask_qty=lvl.get("askQ"),
                                           source="ws"))

            def on_close(*_):
                log.warning("market websocket closed; falling back to polling until reconnect")
                self.mode = "polling"

            streamer.on("message", on_message)
            streamer.on("close", on_close)
            streamer.on("error", lambda e: setattr(self, "last_error", str(e)[:200]))
            if hasattr(streamer, "auto_reconnect"):
                streamer.auto_reconnect(True, 5, 20)
            streamer.connect()
            self._streamer = streamer
            self.mode = "websocket"
            return True
        except Exception as e:  # SDK API drift must not crash the engine
            self.last_error = f"websocket start failed: {type(e).__name__}: {str(e)[:150]}"
            log.warning(self.last_error)
            return False

    # -------------------------------------------------------------- polling
    def poll_once(self) -> int:
        n = 0
        data = self.client.full_quote(self.keys)
        now = time.time()
        for k, v in data.items():
            if self.book.update(quote_from_rest(k, v, now)):
                n += 1
        return n

    def _run(self):
        backoff = self.poll_seconds
        while not self._stop.is_set():
            ws_alive = self.mode == "websocket"
            if not ws_alive:
                try:
                    self.poll_once()
                    backoff = self.poll_seconds
                except Exception as e:
                    self.last_error = f"poll failed: {type(e).__name__}: {str(e)[:150]}"
                    log.warning(self.last_error)
                    backoff = min(backoff * 2, 60)
            self._stop.wait(backoff)

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        if not (self.use_websocket and self._start_ws()):
            self.mode = "polling"
        self._thread = threading.Thread(target=self._run, daemon=True, name="LiveFeed")
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._streamer is not None:
            try:
                self._streamer.disconnect()
            except Exception:
                pass
        self.mode = "stopped"
