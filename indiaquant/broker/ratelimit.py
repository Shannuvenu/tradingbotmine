"""Sliding-window rate limiter matching Upstox's published limits.

https://upstox.com/developer/api-documentation/rate-limiting (checked 2026-10-21)
  Order APIs (place/modify/cancel/multi/GTT), non-registered algo: 10/s, 500/min, 2000/30min
  Standard APIs: 50/s, 500/min, 2000/30min
We run at a safety margin below these numbers.
"""
from __future__ import annotations

import threading
import time
from collections import deque


class SlidingWindowLimiter:
    def __init__(self, limits: list[tuple[float, int]], clock=time.monotonic, sleeper=time.sleep):
        self.limits = limits  # (window_seconds, max_requests)
        self.events: deque[float] = deque()
        self.lock = threading.Lock()
        self.clock, self.sleeper = clock, sleeper
        self.longest = max(w for w, _ in limits)

    def _wait_time(self, now: float) -> float:
        while self.events and now - self.events[0] > self.longest:
            self.events.popleft()
        wait = 0.0
        for window, cap in self.limits:
            in_win = [t for t in self.events if now - t < window]
            if len(in_win) >= cap:
                wait = max(wait, window - (now - in_win[-cap]) + 0.001)
        return wait

    def acquire(self, block: bool = True) -> bool:
        while True:
            with self.lock:
                now = self.clock()
                w = self._wait_time(now)
                if w <= 0:
                    self.events.append(now)
                    return True
            if not block:
                return False
            self.sleeper(w)


def order_limiter(**kw) -> SlidingWindowLimiter:
    return SlidingWindowLimiter([(1.0, 8), (60.0, 400), (1800.0, 1600)], **kw)


def standard_limiter(**kw) -> SlidingWindowLimiter:
    return SlidingWindowLimiter([(1.0, 25), (60.0, 400), (1800.0, 1600)], **kw)
