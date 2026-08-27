from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import cast

from fastapi.testclient import TestClient
from httpx import Response

from app.tests.test_authentication import csrf_token, register
from app.tests.test_job_requirements import create_job_requirement
from app.tests.test_job_targets import create_job_target
from app.tests.test_match_analyses import create_analysis, create_ready_cv_version


def generate_actions(
    client: TestClient,
    analysis_id: str,
    *,
    include_csrf: bool = True,
    payload: dict[str, object] | None = None,
) -> Response:
    headers = {"X-CSRF-Token": csrf_token(client)} if include_csrf else {}
    return cast(
        Response,
        client.post(
            f"/api/v1/match-analyses/{analysis_id}/actions",
            headers=headers,
            json={} if payload is None else payload,
        ),
    )


def create_v3_analysis_with_requirements(
    client: TestClient,
) -> tuple[str, str, str, str, str]:
    document_id, version_id = create_ready_cv_version(client)
    target = create_job_target(client, title="Private platform target")
    target_id = str(target["id"])
    create_job_requirement(
        client,
        target_id=target_id,
        requirement="Private matched Python requirement",
        category="must-have",
        priority=90,
        normalized_skill="Python",
    )
    create_job_requirement(
        client,
        target_id=target_id,
        requirement="Private GCP requirement",
        category="must-have",
        priority=65,
        normalized_skill="GCP",
    )
    should_requirement = cast(
        dict[str, object],
        create_job_requirement(
            client,
            target_id=target_id,
            requirement="Private Kubernetes requirement",
            category="should-have",
            priority=75,
            normalized_skill="Kubernetes",
        ).json(),
    )
    create_job_requirement(
        client,
        target_id=target_id,
        requirement="Private Terraform requirement",
        category="nice-to-have",
        priority=95,
        normalized_skill="Terraform",
    )
    analysis = cast(
        dict[str, object],
        create_analysis(
            client,
            cv_document_version_id=version_id,
            job_target_id=target_id,
            scoring_version="deterministic-v3",
        ).json(),
    )
    return (
        document_id,
        version_id,
        target_id,
        cast(str, analysis["id"]),
        cast(str, should_requirement["id"]),
    )


def test_owner_generates_and_reads_deterministic_actions_from_unmatched_v3_requirements(
    client: TestClient,
) -> None:
    register(client, "actions@example.com")
    _, _, _, analysis_id, should_requirement_id = create_v3_analysis_with_requirements(client)

    first_generation = generate_actions(client, analysis_id)
    first_body = cast(dict[str, object], first_generation.json())
    first_actions = cast(list[dict[str, object]], first_body["data"])
    repeated_generation = generate_actions(client, analysis_id)
    listed_actions = client.get(f"/api/v1/match-analyses/{analysis_id}/actions?limit=1")
    listed_body = cast(dict[str, object], listed_actions.json())
    listed_data = cast(list[dict[str, object]], listed_body["data"])

    assert first_generation.status_code == 201
    assert len(first_actions) == 3
    assert first_actions[0]["category"] == "must-have"
    assert first_actions[0]["priority"] == 265
    assert first_actions[0]["position"] == 1
    assert first_actions[0]["evidenceState"] == "NOT_FOUND_IN_PROVIDED_CV"
    assert first_actions[0]["status"] == "todo"
    assert first_actions[1]["category"] == "should-have"
    assert first_actions[1]["priority"] == 175
    assert first_actions[1]["position"] == 2
    assert first_actions[1]["requirementId"] == should_requirement_id
    assert first_actions[2]["category"] == "nice-to-have"
    assert first_actions[2]["priority"] == 95
    assert first_actions[2]["position"] == 3
    assert all("Private" not in str(action) for action in first_actions)
    assert all("CV_PRIVATE_EVIDENCE_MARKER" not in str(action) for action in first_actions)
    assert all("python" not in cast(str, action["title"]) for action in first_actions)
    assert repeated_generation.status_code == 201
    assert repeated_generation.json()["data"] == first_actions
    assert listed_actions.status_code == 200
    assert listed_data == [first_actions[0]]
    assert listed_body["nextCursor"] is not None


def test_concurrent_action_generation_reuses_one_deterministic_plan(
    client: TestClient,
    second_client: TestClient,
) -> None:
    register(client, "concurrent-actions@example.com")
    _, _, _, analysis_id, _ = create_v3_analysis_with_requirements(client)
    second_client.cookies.update(client.cookies)

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(
            executor.map(
                lambda active_client: generate_actions(active_client, analysis_id),
                (client, second_client),
            )
        )

    response_bodies = [cast(dict[str, object], response.json()) for response in responses]
    response_actions = [cast(list[dict[str, object]], body["data"]) for body in response_bodies]
    listed = client.get(f"/api/v1/match-analyses/{analysis_id}/actions")
    listed_actions = cast(list[dict[str, object]], listed.json()["data"])

    assert all(response.status_code == 201 for response in responses)
    assert response_actions[0] == response_actions[1]
    assert len(listed_actions) == 3
    assert len({action["requirementId"] for action in listed_actions}) == 3


def test_owner_can_update_only_an_action_status(client: TestClient) -> None:
    register(client, "actions-update@example.com")
    _, _, _, analysis_id, _ = create_v3_analysis_with_requirements(client)
    action = cast(dict[str, object], generate_actions(client, analysis_id).json()["data"][0])

    response = client.patch(
        f"/api/v1/match-analyses/{analysis_id}/actions/{action['id']}",
        headers={"X-CSRF-Token": csrf_token(client)},
        json={"status": "completed"},
    )
    override_response = client.patch(
        f"/api/v1/match-analyses/{analysis_id}/actions/{action['id']}",
        headers={"X-CSRF-Token": csrf_token(client)},
        json={"priority": 300},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert override_response.status_code == 422


def test_requirement_changes_create_a_new_stable_analysis_action_plan(client: TestClient) -> None:
    register(client, "actions-history@example.com")
    (
        _,
        version_id,
        target_id,
        analysis_id,
        should_requirement_id,
    ) = create_v3_analysis_with_requirements(client)
    original_actions = cast(
        list[dict[str, object]],
        generate_actions(client, analysis_id).json()["data"],
    )
    updated_requirement = client.patch(
        f"/api/v1/job-targets/{target_id}/requirements/{should_requirement_id}",
        headers={"X-CSRF-Token": csrf_token(client)},
        json={"normalizedSkill": "Go"},
    )
    new_analysis = create_analysis(
        client,
        cv_document_version_id=version_id,
        job_target_id=target_id,
        scoring_version="deterministic-v3",
    )
    new_analysis_id = cast(str, new_analysis.json()["id"])
    new_actions = cast(
        list[dict[str, object]],
        generate_actions(client, new_analysis_id).json()["data"],
    )
    original_actions_after_change = client.get(f"/api/v1/match-analyses/{analysis_id}/actions")

    assert updated_requirement.status_code == 200
    assert new_analysis.status_code == 201
    assert new_analysis_id != analysis_id
    assert original_actions[1]["title"] == "Add evidence for kubernetes"
    assert new_actions[1]["title"] == "Add evidence for go"
    assert original_actions_after_change.json()["data"] == original_actions


def test_target_deletion_cascades_analysis_actions(client: TestClient) -> None:
    register(client, "actions-delete@example.com")
    _, _, target_id, analysis_id, _ = create_v3_analysis_with_requirements(client)
    assert generate_actions(client, analysis_id).status_code == 201

    delete_response = client.delete(
        f"/api/v1/job-targets/{target_id}",
        headers={"X-CSRF-Token": csrf_token(client)},
    )
    actions_response = client.get(f"/api/v1/match-analyses/{analysis_id}/actions")

    assert delete_response.status_code == 204
    assert actions_response.status_code == 404


def test_action_plan_security_and_v2_empty_plan_behavior(
    client: TestClient,
    second_client: TestClient,
) -> None:
    unauthenticated_response = client.get("/api/v1/match-analyses/not-a-uuid/actions")
    register(client, "actions-owner@example.com")
    _, _, _, analysis_id, _ = create_v3_analysis_with_requirements(client)
    action = cast(dict[str, object], generate_actions(client, analysis_id).json()["data"][0])
    no_csrf_response = generate_actions(client, analysis_id, include_csrf=False)
    injected_evidence_response = generate_actions(
        client,
        analysis_id,
        payload={"evidence": [{"term": "python"}]},
    )

    register(second_client, "actions-other@example.com")
    cross_read_response = second_client.get(f"/api/v1/match-analyses/{analysis_id}/actions")
    cross_generate_response = generate_actions(second_client, analysis_id)
    cross_update_response = second_client.patch(
        f"/api/v1/match-analyses/{analysis_id}/actions/{action['id']}",
        headers={"X-CSRF-Token": csrf_token(second_client)},
        json={"status": "completed"},
    )

    _, v2_version_id = create_ready_cv_version(client)
    v2_target = create_job_target(client, title="V2 unchanged target")
    v2_analysis = cast(
        dict[str, object],
        create_analysis(
            client,
            cv_document_version_id=v2_version_id,
            job_target_id=str(v2_target["id"]),
        ).json(),
    )
    v2_actions_response = generate_actions(client, cast(str, v2_analysis["id"]))

    assert unauthenticated_response.status_code == 401
    assert no_csrf_response.status_code == 403
    assert injected_evidence_response.status_code == 422
    assert cross_read_response.status_code == 404
    assert cross_generate_response.status_code == 404
    assert cross_update_response.status_code == 404
    assert v2_actions_response.status_code == 201
    assert v2_actions_response.json()["data"] == []
