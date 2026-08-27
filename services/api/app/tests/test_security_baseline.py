from __future__ import annotations

import logging

from fastapi.testclient import TestClient
from pytest import LogCaptureFixture

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


def test_redact_removes_common_sensitive_career_and_identity_fields() -> None:
    event = {
        "email": "candidate@example.com",
        "cvText": "private CV content",
        "job_description": "private job description",
        "private_object_key": "cv/private-key",
        "session_token": "session-secret",
        "nested": {"csrfToken": "csrf-secret", "safe_field": "allowed"},
    }

    assert redact(event) == {
        "email": "[REDACTED]",
        "cvText": "[REDACTED]",
        "job_description": "[REDACTED]",
        "private_object_key": "[REDACTED]",
        "session_token": "[REDACTED]",
        "nested": {"csrfToken": "[REDACTED]", "safe_field": "allowed"},
    }


def test_request_completion_log_uses_safe_route_template_and_omits_query_values(
    client: TestClient, caplog: LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="app.main")
    private_query_value = "private-cv-content-must-not-be-logged"

    response = client.get(f"/api/v1/health?cvText={private_query_value}")

    assert response.status_code == 200
    completion_records = [
        record for record in caplog.records if record.getMessage() == "request completed"
    ]
    assert len(completion_records) == 1
    event = getattr(completion_records[0], "event", None)
    assert isinstance(event, dict)
    assert event["method"] == "GET"
    assert event["route"] == "/health"
    assert event["status_code"] == 200
    assert isinstance(event["duration_ms"], int)
    assert event["duration_ms"] >= 0
    assert private_query_value not in str(event)
    assert "query" not in event
    assert "path" not in event
