"""Cross-request coordination: rate limits, the regenerate cooldown, and
per-username generation locks.

Two backends, picked from REDIS_URL:

  - Memory (default) — process-local. Correct for a single instance with a
    single worker, which is the free-tier deployment.
  - Redis — shared by every worker and instance, so the API can run behind a
    load balancer (several replicas, or WEB_CONCURRENCY > 1) and still enforce
    one limit, one cooldown, and one in-flight ingest per username.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from collections import defaultdict, deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Request

logger = logging.getLogger("proof.coordination")

# Prune idle rate-limit keys once the table grows past this (memory backend).
_MAX_KEYS = 10_000
# Upper bound on one generation holding a username lock (GitHub + LLM). A
# crashed holder's Redis lock expires after this instead of blocking forever.
_LOCK_TTL = 180


class MemoryCoordinator:
    name = "memory"

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = {}
        self._hits_lock = threading.Lock()
        self._generated: dict[str, float] = {}
        self._locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def allow(self, bucket: str, key: str, limit: int, window: int) -> bool:
        """Sliding window: record a hit unless `limit` were already seen in `window` s."""
        now = time.monotonic()
        cutoff = now - window
        with self._hits_lock:
            if len(self._hits) > _MAX_KEYS:
                for k in [k for k, q in self._hits.items() if not q or q[-1] <= cutoff]:
                    del self._hits[k]
            q = self._hits.setdefault(f"{bucket}:{key}", deque())
            while q and q[0] <= cutoff:
                q.popleft()
            if len(q) >= limit:
                return False
            q.append(now)
            return True

    async def recently_generated(self, username: str, within: int) -> bool:
        last = self._generated.get(username)
        return last is not None and time.monotonic() - last <= within

    async def mark_generated(self, username: str, ttl: int) -> None:
        self._generated[username] = time.monotonic()

    @asynccontextmanager
    async def generation_lock(self, username: str) -> AsyncIterator[None]:
        async with self._locks[username]:
            yield

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        pass


class RedisCoordinator:
    name = "redis"

    def __init__(self, url: str) -> None:
        import redis.asyncio as redis  # lazy: the memory backend needs no client

        self._redis = redis.from_url(url, decode_responses=True)

    async def allow(self, bucket: str, key: str, limit: int, window: int) -> bool:
        """Fixed window per `window` seconds: one atomic INCR + EXPIRE round trip."""
        slot = int(time.time() // window)
        rkey = f"rl:{bucket}:{key}:{slot}"
        async with self._redis.pipeline(transaction=True) as pipe:
            count, _ = await pipe.incr(rkey).expire(rkey, window).execute()
        return count <= limit

    async def recently_generated(self, username: str, within: int) -> bool:
        return bool(await self._redis.exists(f"gen:{username}"))

    async def mark_generated(self, username: str, ttl: int) -> None:
        await self._redis.set(f"gen:{username}", "1", ex=ttl)

    @asynccontextmanager
    async def generation_lock(self, username: str) -> AsyncIterator[None]:
        # Token-checked lock (redis-py releases via a Lua compare-and-delete),
        # so one instance can never release another instance's lock.
        lock = self._redis.lock(
            f"lock:gen:{username}", timeout=_LOCK_TTL, blocking_timeout=_LOCK_TTL
        )
        if not await lock.acquire():
            raise TimeoutError(f"timed out waiting for the {username} generation lock")
        try:
            yield
        finally:
            try:
                await lock.release()
            except Exception as exc:  # expired already, or Redis unreachable
                logger.warning(
                    "could not release generation lock for %s (%s); it expires after %ss",
                    username,
                    exc,
                    _LOCK_TTL,
                )

    async def ping(self) -> bool:
        try:
            return bool(await self._redis.ping())
        except Exception:
            return False

    async def close(self) -> None:
        await self._redis.aclose()


def create(redis_url: str | None) -> MemoryCoordinator | RedisCoordinator:
    return RedisCoordinator(redis_url) if redis_url else MemoryCoordinator()


def client_ip(request: Request) -> str:
    """Best-effort client IP. Behind Vercel's rewrite proxy the socket peer is
    Vercel, so prefer the left-most X-Forwarded-For entry it sets."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
