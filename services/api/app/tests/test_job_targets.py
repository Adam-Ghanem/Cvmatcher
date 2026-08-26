from __future__ import annotations

from typing import cast

from fastapi.testclient import TestClient

from app.tests.test_authentication import csrf_token, register


def create_job_target(
    client: TestClient,
    *,
    title: str = "Staff platform engineer",
) -> dict[str, object]:
    response = client.post(
        "/api/v1/job-targets",
        headers={"X-CSRF-Token": csrf_token(client)},
        json={
            "company": "Northstar Systems",
            "jobDescription": "Lead the platform engineering function and build reliable systems "
            "for a growing product organization.",
            "location": "Remote",
            "title": title,
        },
    )

    assert response.status_code == 201
    return cast(dict[str, object], response.json())


def test_owner_can_save_a_private_target_role_without_job_text_in_response(
    client: TestClient,
) -> None:
    register(client, "candidate@example.com")

    target = create_job_target(client)

    assert target["title"] == "Staff platform engineer"
    assert target["company"] == "Northstar Systems"
    assert target["location"] == "Remote"
    assert "jobDescription" not in target
    assert "Lead the platform engineering" not in str(target)


def test_job_target_list_is_scoped_to_the_authenticated_owner(
    client: TestClient,
    second_client: TestClient,
) -> None:
    register(client, "owner@example.com")
    create_job_target(client, title="Owner target")
    register(second_client, "other@example.com")
    create_job_target(second_client, title="Other target")

    response = client.get("/api/v1/job-targets")

    body = cast(dict[str, object], response.json())
    targets = cast(list[dict[str, object]], body["data"])
    assert response.status_code == 200
    assert [target["title"] for target in targets] == ["Owner target"]


def test_job_target_creation_requires_csrf_and_valid_description(client: TestClient) -> None:
    register(client, "candidate@example.com")

    csrf_response = client.post(
        "/api/v1/job-targets",
        json={
            "jobDescription": (
                "A valid but untrusted pasted role description that is long enough for validation. "
                "It remains private application data."
            ),
            "title": "Staff platform engineer",
        },
    )
    invalid_response = client.post(
        "/api/v1/job-targets",
        headers={"X-CSRF-Token": csrf_token(client)},
        json={
            "jobDescription": "Too short",
            "title": "Staff platform engineer",
        },
    )

    assert csrf_response.status_code == 403
    assert invalid_response.status_code == 422
