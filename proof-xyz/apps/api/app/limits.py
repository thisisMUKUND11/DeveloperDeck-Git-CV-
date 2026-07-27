"""In-process sliding-window rate limiting for the expensive endpoints.

`/api/generate` is unauthenticated, and a cache miss costs a GitHub fan-out
(~9 calls per repo) plus an LLM call. Without a bound, one script can exhaust
the hourly GitHub token budget and run up the LLM bill in minutes.

Deliberately in-memory, not Redis: the API runs as a single web instance, so a
process-local window is accurate, adds no dependency, and cannot itself fail.
The trade-off is that counters reset when the container restarts — acceptable,
since the fixed cost of a restart is far smaller than the abuse it bounds.
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict, deque

# Stop tracking clients once the table gets large, oldest-touched first. Bounds
# memory against an attacker cycling through spoofed forwarding headers.
_MAX_TRACKED_KEYS = 10_000


class SlidingWindowLimiter:
    """Allow at most `limit` hits per `window_seconds` for each key."""

    def __init__(self, limit: int, window_seconds: float = 3600.0) -> None:
        self._limit = limit
        self._window = window_seconds
        self._hits: OrderedDict[str, deque[float]] = OrderedDict()
        self._lock = threading.Lock()

    def try_acquire(self, key: str) -> tuple[bool, int]:
        """Record a hit if the key is under its limit.

        Returns (allowed, retry_after_seconds). `retry_after_seconds` is 0 when
        allowed. Only call this for work you're actually about to do — a hit is
        consumed on every allowed call.
        """
        # monotonic(): immune to NTP/clock adjustments, unlike wall time.
        now = time.monotonic()
        cutoff = now - self._window
        with self._lock:
            hits = self._hits.get(key)
            if hits is None:
                hits = deque()
                self._hits[key] = hits
            self._hits.move_to_end(key)

            while hits and hits[0] <= cutoff:
                hits.popleft()

            if len(hits) >= self._limit:
                # The oldest hit in the window is the one that has to age out.
                return False, max(1, int(hits[0] + self._window - now) + 1)

            hits.append(now)
            self._evict_locked()
            return True, 0

    def _evict_locked(self) -> None:
        """Drop empty and least-recently-touched keys. Caller holds the lock."""
        if len(self._hits) <= _MAX_TRACKED_KEYS:
            return
        for key in [k for k, v in self._hits.items() if not v]:
            del self._hits[key]
        while len(self._hits) > _MAX_TRACKED_KEYS:
            self._hits.popitem(last=False)


def client_key(headers, fallback: str | None) -> str:
    """Best-effort stable identifier for the caller.

    The browser talks to the Next.js app, which proxies `/api/*` to this
    service, so `request.client.host` is the proxy — the original address only
    survives in X-Forwarded-For, whose first entry is the client.

    This header is spoofable when the API is reachable directly, so per-client
    limiting is a courtesy bound, not a security boundary. The global cap in
    main.py is what actually protects the budget.
    """
    forwarded = headers.get("x-forwarded-for")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    return fallback or "unknown"
