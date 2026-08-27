from __future__ import annotations

import asyncio
import math
import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class RateLimitPolicy:
    """A server-controlled request budget for one route class."""

    name: str
    limit: int
    window_seconds: int

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Rate-limit policy names must not be empty.")
        if self.limit < 1:
            raise ValueError("Rate-limit policy limits must be positive.")
        if self.window_seconds < 1:
            raise ValueError("Rate-limit policy windows must be positive.")


@dataclass(frozen=True, slots=True)
class RateLimitBackendResult:
    allowed: bool
    remaining: int
    reset_after_seconds: int


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    allowed: bool
    limit: int
    remaining: int
    reset_after_seconds: int
    retry_after_seconds: int | None
    backend_available: bool


class RateLimitBackendUnavailable(Exception):
    """The configured rate-limit backend cannot safely serve a decision."""


class RateLimitBackend(Protocol):
    """Server-side storage contract for an atomic request-budget decision."""

    async def check(
        self,
        *,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> RateLimitBackendResult: ...


class InMemoryRateLimitBackend:
    """Single-process backend for local and test deployments only."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._buckets: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def check(
        self,
        *,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> RateLimitBackendResult:
        now = self._clock()
        earliest_allowed = now - window_seconds
        async with self._lock:
            bucket = self._buckets[key]
            while bucket and bucket[0] <= earliest_allowed:
                bucket.popleft()

            if len(bucket) >= limit:
                reset_after_seconds = self._seconds_until(bucket[0] + window_seconds, now)
                return RateLimitBackendResult(
                    allowed=False,
                    remaining=0,
                    reset_after_seconds=reset_after_seconds,
                )

            bucket.append(now)
            reset_after_seconds = self._seconds_until(bucket[0] + window_seconds, now)
            return RateLimitBackendResult(
                allowed=True,
                remaining=limit - len(bucket),
                reset_after_seconds=reset_after_seconds,
            )

    @staticmethod
    def _seconds_until(timestamp: float, now: float) -> int:
        return max(1, math.ceil(timestamp - now))


class RateLimitService:
    """Applies named policies through a provider without exposing provider details."""

    def __init__(
        self,
        backend: RateLimitBackend,
        *,
        fail_closed_on_backend_error: bool,
    ) -> None:
        self._backend = backend
        self._fail_closed_on_backend_error = fail_closed_on_backend_error

    async def check(self, *, policy: RateLimitPolicy, key: str) -> RateLimitDecision:
        try:
            result = await self._backend.check(
                key=f"{policy.name}:{key}",
                limit=policy.limit,
                window_seconds=policy.window_seconds,
            )
        except RateLimitBackendUnavailable:
            return self._backend_unavailable_decision(policy)
        except Exception:
            return self._backend_unavailable_decision(policy)

        return RateLimitDecision(
            allowed=result.allowed,
            limit=policy.limit,
            remaining=result.remaining,
            reset_after_seconds=result.reset_after_seconds,
            retry_after_seconds=(result.reset_after_seconds if not result.allowed else None),
            backend_available=True,
        )

    def _backend_unavailable_decision(self, policy: RateLimitPolicy) -> RateLimitDecision:
        if self._fail_closed_on_backend_error:
            return RateLimitDecision(
                allowed=False,
                limit=policy.limit,
                remaining=0,
                reset_after_seconds=policy.window_seconds,
                retry_after_seconds=policy.window_seconds,
                backend_available=False,
            )
        return RateLimitDecision(
            allowed=True,
            limit=policy.limit,
            remaining=policy.limit,
            reset_after_seconds=policy.window_seconds,
            retry_after_seconds=None,
            backend_available=False,
        )


class InMemoryRateLimiter:
    """Compatibility wrapper for existing local callers and tests."""

    def __init__(
        self,
        max_requests: int,
        window_seconds: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._policy = RateLimitPolicy(
            name="legacy",
            limit=max_requests,
            window_seconds=math.ceil(window_seconds),
        )
        self._service = RateLimitService(
            InMemoryRateLimitBackend(clock=clock),
            fail_closed_on_backend_error=True,
        )

    async def allow(self, key: str) -> bool:
        return (await self._service.check(policy=self._policy, key=key)).allowed
