from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import cast

from fastapi.testclient import TestClient
from httpx import Response


def csrf_token(client: TestClient) -> str:
    response = client.get("/api/v1/auth/csrf")

    assert response.status_code == 200
    body = cast(dict[str, object], response.json())
    token = cast(str, body["csrfToken"])
    assert token == client.cookies.get("cvmatcher_csrf")
    return token


def register(
    client: TestClient,
    email: str,
    password: str = "A-str0ng-password!",
) -> dict[str, object]:
    response = client.post(
        "/api/v1/auth/register",
        headers={"X-CSRF-Token": csrf_token(client)},
        json={"email": email, "password": password},
    )

    assert response.status_code == 201
    assert "cvmatcher_session" in response.headers["set-cookie"]
    assert "HttpOnly" in response.headers["set-cookie"]
    body = cast(dict[str, object], response.json())
    user = cast(dict[str, object], body["user"])
    assert user["email"] == email
    assert "password" not in response.text.lower()
    return cast(dict[str, object], response.json())


def test_register_issues_an_opaque_session_and_me_returns_the_server_principal(
    client: TestClient,
) -> None:
    register(client, "candidate@example.com")

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json()["user"]["email"] == "candidate@example.com"
    assert "authSubject" not in response.json()["user"]


def test_concurrent_registration_returns_a_safe_conflict_for_one_request(
    client: TestClient,
    second_client: TestClient,
) -> None:
    def register_concurrently(active_client: TestClient) -> Response:
        return cast(
            Response,
            active_client.post(
                "/api/v1/auth/register",
                headers={"X-CSRF-Token": csrf_token(active_client)},
                json={"email": "race@example.com", "password": "A-str0ng-password!"},
            ),
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(register_concurrently, (client, second_client)))

    status_codes = sorted(response.status_code for response in responses)
    conflict_response = next(response for response in responses if response.status_code == 409)

    assert status_codes == [201, 409]
    assert conflict_response.json()["error"]["code"] == "ACCOUNT_UNAVAILABLE"
    assert "integrity" not in conflict_response.text.casefold()


def test_protected_identity_endpoint_rejects_anonymous_requests(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


def test_state_changing_authentication_route_requires_a_matching_csrf_token(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "candidate@example.com", "password": "A-str0ng-password!"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CSRF_VALIDATION_FAILED"


def test_logout_revokes_the_server_session(client: TestClient) -> None:
    register(client, "candidate@example.com")

    response = client.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": csrf_token(client)},
    )

    assert response.status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401
