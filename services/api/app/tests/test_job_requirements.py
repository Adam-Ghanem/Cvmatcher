from __future__ import annotations

from typing import Any, cast

from fastapi.testclient import TestClient
from httpx import Response

from app.tests.test_authentication import csrf_token, register
from app.tests.test_job_targets import create_job_target


def create_job_requirement(
    client: TestClient,
    *,
    target_id: str,
    requirement: str = "Build reliable Python services",
    category: str = "must-have",
    priority: int = 90,
    normalized_skill: str | None = "Python",
    source_reference: str | None = "Job description: engineering requirements",
    review_state: str = "reviewed",
    include_csrf: bool = True,
) -> Response:
    headers = {"X-CSRF-Token": csrf_token(client)} if include_csrf else {}
    payload: dict[str, Any] = {
        "requirement": requirement,
        "category": category,
        "priority": priority,
        "reviewState": review_state,
    }
    if normalized_skill is not None:
        payload["normalizedSkill"] = normalized_skill
    if source_reference is not None:
        payload["sourceReference"] = source_reference
    return cast(
        Response,
        client.post(
            f"/api/v1/job-targets/{target_id}/requirements",
            headers=headers,
            json=payload,
        ),
    )


def test_owner_can_create_and_page_private_structured_requirements(client: TestClient) -> None:
    register(client, "requirements@example.com")
    target = create_job_target(client, title="Platform engineer")
    target_id = str(target["id"])
    first_response = create_job_requirement(
        client,
        target_id=target_id,
        requirement="Build reliable Python services",
        category="must-have",
        priority=90,
        normalized_skill="Python",
    )
    second_response = create_job_requirement(
        client,
        target_id=target_id,
        requirement="Improve deployment automation",
        category="should-have",
        priority=70,
        normalized_skill="CI/CD",
    )

    first_body = cast(dict[str, object], first_response.json())
    second_body = cast(dict[str, object], second_response.json())
    first_page = client.get(f"/api/v1/job-targets/{target_id}/requirements?limit=1")
    first_page_body = cast(dict[str, object], first_page.json())
    first_page_data = cast(list[dict[str, object]], first_page_body["data"])
    cursor = cast(str, first_page_body["nextCursor"])
    second_page = client.get(
        f"/api/v1/job-targets/{target_id}/requirements?limit=1&cursor={cursor}"
    )
    second_page_body = cast(dict[str, object], second_page.json())
    second_page_data = cast(list[dict[str, object]], second_page_body["data"])

    assert first_response.status_code == 201
    assert first_body["category"] == "must-have"
    assert first_body["normalizedSkill"] == "python"
    assert first_body["priority"] == 90
    assert first_body["normalizationVersion"] == "manual-v1"
    assert first_body["reviewState"] == "reviewed"
    assert first_page.status_code == 200
    assert second_page.status_code == 200
    assert {first_page_data[0]["id"], second_page_data[0]["id"]} == {
        first_body["id"],
        second_body["id"],
    }
    assert first_page_data[0]["id"] == first_body["id"]
    assert second_page_body["nextCursor"] is None
    assert "Lead the platform engineering function" not in first_page.text
    assert "jobDescription" not in first_page.text


def test_owner_can_update_a_structured_requirement_without_changing_its_normalization_version(
    client: TestClient,
) -> None:
    register(client, "requirement-update@example.com")
    target = create_job_target(client)
    created = cast(
        dict[str, object],
        create_job_requirement(client, target_id=str(target["id"])).json(),
    )

    response = client.patch(
        f"/api/v1/job-targets/{target['id']}/requirements/{created['id']}",
        headers={"X-CSRF-Token": csrf_token(client)},
        json={
            "category": "should-have",
            "priority": 65,
            "reviewState": "user-confirmed",
            "normalizedSkill": "Python  ",
        },
    )
    body = cast(dict[str, object], response.json())

    assert response.status_code == 200
    assert body["category"] == "should-have"
    assert body["priority"] == 65
    assert body["reviewState"] == "user-confirmed"
    assert body["normalizedSkill"] == "python"
    assert body["normalizationVersion"] == "manual-v1"


def test_requirement_writes_validate_csrf_and_enforce_owner_boundaries(
    client: TestClient,
    second_client: TestClient,
) -> None:
    register(client, "requirement-owner@example.com")
    target = create_job_target(client)
    created = cast(
        dict[str, object],
        create_job_requirement(client, target_id=str(target["id"])).json(),
    )
    no_csrf_response = create_job_requirement(
        client,
        target_id=str(target["id"]),
        include_csrf=False,
    )
    invalid_response = create_job_requirement(
        client,
        target_id=str(target["id"]),
        category="required",
    )

    register(second_client, "requirement-other@example.com")
    cross_list_response = second_client.get(f"/api/v1/job-targets/{target['id']}/requirements")
    cross_update_response = second_client.patch(
        f"/api/v1/job-targets/{target['id']}/requirements/{created['id']}",
        headers={"X-CSRF-Token": csrf_token(second_client)},
        json={"priority": 40},
    )
    cross_delete_response = second_client.delete(
        f"/api/v1/job-targets/{target['id']}/requirements/{created['id']}",
        headers={"X-CSRF-Token": csrf_token(second_client)},
    )

    assert no_csrf_response.status_code == 403
    assert invalid_response.status_code == 422
    assert cross_list_response.status_code == 404
    assert cross_update_response.status_code == 404
    assert cross_delete_response.status_code == 404
    assert cross_update_response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
