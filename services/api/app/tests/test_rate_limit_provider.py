from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.rate_limit import (
    InMemoryRateLimitBackend,
    RateLimitBackend,
    RateLimitBackendResult,
    RateLimitBackendUnavailable,
    RateLimitPolicy,
    RateLimitService,
)
from app.main import create_app


async def test_rate_limit_decision_exposes_remaining_retry_and_reset_metadata() -> None:
    clock_value = 100.0

    def clock() -> float:
        return clock_value

    service = RateLimitService(
        InMemoryRateLimitBackend(clock=clock),
        fail_closed_on_backend_error=True,
    )
    policy = RateLimitPolicy(name="test", limit=2, window_seconds=60)

    first = await service.check(policy=policy, key="client")
    second = await service.check(policy=policy, key="client")
    limited = await service.check(policy=policy, key="client")

    assert first.allowed
    assert first.remaining == 1
    assert first.reset_after_seconds == 60
    assert second.allowed
    assert second.remaining == 0
    assert not limited.allowed
    assert limited.retry_after_seconds == 60
    assert limited.reset_after_seconds == 60

    clock_value += 60
    reset = await service.check(policy=policy, key="client")

    assert reset.allowed
    assert reset.remaining == 1


async def test_shared_backend_enforces_one_budget_across_service_instances() -> None:
    backend = InMemoryRateLimitBackend()
    first_instance = RateLimitService(backend, fail_closed_on_backend_error=True)
    second_instance = RateLimitService(backend, fail_closed_on_backend_error=True)
    policy = RateLimitPolicy(name="shared", limit=1, window_seconds=60)

    assert (await first_instance.check(policy=policy, key="client")).allowed
    assert not (await second_instance.check(policy=policy, key="client")).allowed


class UnavailableRateLimitBackend(RateLimitBackend):
    async def check(
        self,
        *,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> RateLimitBackendResult:
        raise RateLimitBackendUnavailable("backend unavailable")


async def test_backend_failure_fails_closed_without_provider_details() -> None:
    service = RateLimitService(
        UnavailableRateLimitBackend(),
        fail_closed_on_backend_error=True,
    )

    decision = await service.check(
        policy=RateLimitPolicy(name="general", limit=10, window_seconds=60),
        key="client",
    )

    assert not decision.allowed
    assert decision.backend_available is False
    assert decision.retry_after_seconds == 60


def test_production_settings_reject_the_local_rate_limit_backend(settings: Settings) -> None:
    try:
        Settings(
            app_env="production",
            database_url=settings.database_url,
            cors_allowed_origins=["https://app.cvmatcher.example"],
            session_hmac_secret="not-a-development-secret-that-is-at-least-thirty-two-bytes",
            private_storage_root="configured-private-adapter-root",
            rate_limit_backend="local",
        )
    except ValueError as exc:
        assert "shared rate-limit backend" in str(exc)
    else:
        raise AssertionError("Production settings accepted the local rate-limit backend.")


def test_auth_and_expensive_routes_use_distinct_policy_budgets(settings: Settings) -> None:
    constrained_settings = settings.model_copy(
        update={
            "rate_limit_requests_per_minute": 2,
            "auth_rate_limit_requests_per_minute": 1,
            "expensive_rate_limit_requests_per_minute": 1,
        }
    )
    application = create_app(constrained_settings)

    with TestClient(application) as client:
        auth_response = client.get("/api/v1/auth/me")
        general_response = client.get("/api/v1/cv-documents")
        expensive_response = client.post("/api/v1/match-analyses", json={})
        limited_expensive_response = client.post("/api/v1/match-analyses", json={})

    assert auth_response.status_code == 401
    assert auth_response.headers["ratelimit-limit"] == "1"
    assert general_response.status_code == 401
    assert general_response.headers["ratelimit-limit"] == "2"
    assert expensive_response.status_code == 401
    assert expensive_response.headers["ratelimit-limit"] == "1"
    assert limited_expensive_response.status_code == 429
    assert limited_expensive_response.json()["error"]["code"] == "RATE_LIMITED"
    assert limited_expensive_response.headers["retry-after"] == "60"


def test_unavailable_rate_limit_backend_returns_a_safe_http_error(settings: Settings) -> None:
    application = create_app(
        settings,
        rate_limit_backend_factory=lambda _: UnavailableRateLimitBackend(),
    )

    with TestClient(application) as client:
        response = client.get("/api/v1/cv-documents")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "RATE_LIMIT_UNAVAILABLE"
    assert "backend" not in response.json()["error"]["message"].casefold()
    assert response.headers["retry-after"] == "60"


async def test_rate_limit_protocol_is_provider_injectable() -> None:
    def factory() -> RateLimitBackend:
        return InMemoryRateLimitBackend()

    service = RateLimitService(factory(), fail_closed_on_backend_error=True)

    assert (await service.check(policy=RateLimitPolicy("test", 1, 60), key="client")).allowed


def test_cors_exposes_rate_limit_headers_to_an_allowed_browser(client: TestClient) -> None:
    response = client.get(
        "/api/v1/auth/me",
        headers={"Origin": "http://localhost:3000"},
    )

    assert response.status_code == 401
    exposed_headers = {
        header.strip().casefold()
        for header in response.headers["access-control-expose-headers"].split(",")
    }
    assert {
        "x-request-id",
        "ratelimit-limit",
        "ratelimit-remaining",
        "ratelimit-reset",
        "retry-after",
    }.issubset(exposed_headers)
