from __future__ import annotations

from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_health_returns_status_and_correlation_id(client: TestClient) -> None:
    response = client.get(
        "/api/v1/health",
        headers={"X-Request-ID": "3f79e747-17ab-4c80-9e5a-4a9e438471f8"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["x-request-id"] == "3f79e747-17ab-4c80-9e5a-4a9e438471f8"


def test_invalid_correlation_id_is_replaced_with_safe_uuid(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"X-Request-ID": "not-a-valid-id\nforged"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] != "not-a-valid-id\nforged"
    UUID(response.headers["x-request-id"])


def test_health_includes_security_headers(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def test_cors_rejects_unlisted_origin(client: TestClient) -> None:
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "https://attacker.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 400
    assert response.headers.get("access-control-allow-origin") is None


def test_readiness_returns_safe_service_unavailable_when_database_is_down(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def database_is_unavailable(_: object) -> bool:
        return False

    monkeypatch.setattr("app.api.health.is_database_ready", database_is_unavailable)
    response = client.get("/api/v1/ready")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "DEPENDENCY_UNAVAILABLE"
    assert "database" not in response.json()["error"]["message"].lower()


def test_unexpected_downstream_failure_returns_safe_error_envelope(
    application: FastAPI,
    client: TestClient,
) -> None:
    @application.get("/api/v1/test-unexpected-error")
    async def raise_unexpected_error() -> None:
        raise RuntimeError("database password: should never reach a user")

    response = client.get("/api/v1/test-unexpected-error")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "password" not in response.json()["error"]["message"].lower()
    assert response.headers["x-content-type-options"] == "nosniff"


def test_rejects_oversized_declared_non_upload_request_before_routing(client: TestClient) -> None:
    response = client.post(
        "/api/v1/health",
        headers={
            "Content-Length": str(256 * 1024 + 1),
            "Origin": "http://localhost:3000",
        },
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "REQUEST_TOO_LARGE"
    assert "x-request-id" in response.headers
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
