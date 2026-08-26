from __future__ import annotations

from app.core.logging import redact
from app.core.rate_limit import InMemoryRateLimiter


async def test_rate_limiter_blocks_the_next_request_inside_its_window() -> None:
    clock_value = 100.0

    def clock() -> float:
        return clock_value

    limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60, clock=clock)

    assert await limiter.allow("127.0.0.1")
    assert await limiter.allow("127.0.0.1")
    assert not await limiter.allow("127.0.0.1")


def test_redact_removes_nested_sensitive_values() -> None:
    event = {
        "request": {
            "authorization": "Bearer secret-token",
            "document_content": "private CV content",
            "safe_field": "allowed",
        }
    }

    assert redact(event) == {
        "request": {
            "authorization": "[REDACTED]",
            "document_content": "[REDACTED]",
            "safe_field": "allowed",
        }
    }
