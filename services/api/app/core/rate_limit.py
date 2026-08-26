from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from collections.abc import Callable
from typing import Protocol


class RateLimiter(Protocol):
    async def allow(self, key: str) -> bool: ...


class InMemoryRateLimiter:
    """Single-process request limiter suitable only for local and Phase 1 deployments."""

    def __init__(
        self,
        max_requests: int,
        window_seconds: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._clock = clock
        self._buckets: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def allow(self, key: str) -> bool:
        now = self._clock()
        earliest_allowed = now - self._window_seconds
        async with self._lock:
            bucket = self._buckets[key]
            while bucket and bucket[0] <= earliest_allowed:
                bucket.popleft()
            if len(bucket) >= self._max_requests:
                return False
            bucket.append(now)
            return True
