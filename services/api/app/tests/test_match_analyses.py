from __future__ import annotations

from typing import cast
from uuid import uuid4

from fastapi.testclient import TestClient
from httpx import Response

from app.tests.test_authentication import csrf_token, register
from app.tests.test_extraction import upload_docx
from app.tests.test_job_requirements import create_job_requirement
from app.tests.test_job_targets import create_job_target

PRIVATE_CV_TEXT = (
    "Python TypeScript React SQL PostgreSQL AWS Docker 5+ years experience "
    "education skills candidate@example.com CV_PRIVATE_EVIDENCE_MARKER"
)


def create_ready_cv_version(client: TestClient) -> tuple[str, str]:
    document = upload_docx(client, PRIVATE_CV_TEXT)
    version = cast(dict[str, object], document["latestVersion"])
    extraction_response = client.post(
        f"/api/v1/cv-documents/{document['id']}/versions/{version['id']}/extraction",
        headers={"X-CSRF-Token": csrf_token(client)},
    )

    assert extraction_response.status_code == 200
    assert extraction_response.json()["status"] == "succeeded"
    return str(document["id"]), str(version["id"])


def create_analysis(
    client: TestClient,
    *,
    cv_document_version_id: str,
    job_target_id: str,
    include_csrf: bool = True,
    scoring_version: str | None = None,
) -> Response:
    headers = {"X-CSRF-Token": csrf_token(client)} if include_csrf else {}

    payload: dict[str, str] = {
        "cvDocumentVersionId": cv_document_version_id,
        "jobTargetId": job_target_id,
    }
    if scoring_version is not None:
        payload["scoringVersion"] = scoring_version
    return cast(
        Response,
        client.post(
            "/api/v1/match-analyses",
            headers=headers,
            json=payload,
        ),
    )


def test_match_analysis_requires_authentication_and_csrf(client: TestClient) -> None:
    unauthenticated_response = create_analysis(
        client,
        cv_document_version_id=str(uuid4()),
        job_target_id=str(uuid4()),
    )

    assert unauthenticated_response.status_code == 401

    register(client, "candidate@example.com")
    _, version_id = create_ready_cv_version(client)
    target = create_job_target(client)

    csrf_response = create_analysis(
        client,
        cv_document_version_id=version_id,
        job_target_id=str(target["id"]),
        include_csrf=False,
    )

    assert csrf_response.status_code == 403


def test_owner_can_create_and_reuse_a_private_deterministic_match_analysis(
    client: TestClient,
) -> None:
    register(client, "candidate@example.com")
    _, version_id = create_ready_cv_version(client)
    target = create_job_target(client)

    first_response = create_analysis(
        client,
        cv_document_version_id=version_id,
        job_target_id=str(target["id"]),
    )
    second_response = create_analysis(
        client,
        cv_document_version_id=version_id,
        job_target_id=str(target["id"]),
    )

    first_body = cast(dict[str, object], first_response.json())
    second_body = cast(dict[str, object], second_response.json())
    components = cast(list[dict[str, object]], first_body["components"])
    gaps = cast(list[dict[str, object]], first_body["gaps"])

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert first_body["id"] == second_body["id"]
    assert first_body["scoringVersion"] == "deterministic-v2"
    assert isinstance(first_body["overallScore"], int)
    assert {component["key"] for component in components} == {
        "skills",
        "experience",
        "keywords",
        "education",
        "ats",
    }
    assert all(component["score"] in range(0, 101) for component in components)
    assert all("matchedTerms" in component for component in components)
    assert all("notFoundTerms" in component for component in components)
    assert all(gap["state"] == "NOT_FOUND_IN_PROVIDED_CV" for gap in gaps)
    owner_read_response = client.get(f"/api/v1/match-analyses/{first_body['id']}")

    assert owner_read_response.status_code == 200
    assert owner_read_response.json() == first_body
    assert PRIVATE_CV_TEXT not in first_response.text
    assert PRIVATE_CV_TEXT not in owner_read_response.text
    assert "Lead the platform engineering function" not in first_response.text
    assert "jobDescription" not in first_body
    assert "cvDocumentVersionId" not in first_body


def test_match_analysis_requires_a_successful_private_extraction(client: TestClient) -> None:
    register(client, "candidate@example.com")
    document = upload_docx(client, PRIVATE_CV_TEXT)
    version = cast(dict[str, object], document["latestVersion"])
    target = create_job_target(client)

    response = create_analysis(
        client,
        cv_document_version_id=str(version["id"]),
        job_target_id=str(target["id"]),
    )

    body = cast(dict[str, object], response.json())
    error = cast(dict[str, object], body["error"])
    assert response.status_code == 409
    assert error["code"] == "CV_TEXT_NOT_READY"


def test_successful_but_unreadable_extraction_cannot_create_analysis(client: TestClient) -> None:
    register(client, "unreadable@example.com")
    document = upload_docx(client, "")
    version = cast(dict[str, object], document["latestVersion"])
    extraction_response = client.post(
        f"/api/v1/cv-documents/{document['id']}/versions/{version['id']}/extraction",
        headers={"X-CSRF-Token": csrf_token(client)},
    )
    target = create_job_target(client)

    response = create_analysis(
        client,
        cv_document_version_id=str(version["id"]),
        job_target_id=str(target["id"]),
        scoring_version="deterministic-v3",
    )

    assert extraction_response.status_code == 200
    assert extraction_response.json()["readiness"]["state"] == "blocked"
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CV_TEXT_NOT_READY"


def test_v3_analysis_uses_owned_reviewed_requirements_and_preserves_v2_history(
    client: TestClient,
) -> None:
    register(client, "v3@example.com")
    _, version_id = create_ready_cv_version(client)
    target = create_job_target(client, title="V3 platform target")
    target_id = str(target["id"])
    create_job_requirement(
        client,
        target_id=target_id,
        requirement="Build Python services",
        category="must-have",
        priority=100,
        normalized_skill="Python",
    )
    requirement_response = create_job_requirement(
        client,
        target_id=target_id,
        requirement="Operate Docker workloads",
        category="should-have",
        priority=100,
        normalized_skill="Docker",
    )
    v2_response = create_analysis(
        client,
        cv_document_version_id=version_id,
        job_target_id=target_id,
    )
    first_v3_response = create_analysis(
        client,
        cv_document_version_id=version_id,
        job_target_id=target_id,
        scoring_version="deterministic-v3",
    )
    first_v3_body = cast(dict[str, object], first_v3_response.json())
    repeated_v3_response = create_analysis(
        client,
        cv_document_version_id=version_id,
        job_target_id=target_id,
        scoring_version="deterministic-v3",
    )
    requirement = cast(dict[str, object], requirement_response.json())
    update_response = client.patch(
        f"/api/v1/job-targets/{target_id}/requirements/{requirement['id']}",
        headers={"X-CSRF-Token": csrf_token(client)},
        json={"normalizedSkill": "Kubernetes"},
    )
    second_v3_response = create_analysis(
        client,
        cv_document_version_id=version_id,
        job_target_id=target_id,
        scoring_version="deterministic-v3",
    )
    historic_v2_response = client.get(f"/api/v1/match-analyses/{v2_response.json()['id']}")

    assert v2_response.status_code == 201
    assert v2_response.json()["scoringVersion"] == "deterministic-v2"
    assert first_v3_response.status_code == 201
    assert first_v3_body["scoringVersion"] == "deterministic-v3"
    assert first_v3_body["overallScore"] == 100
    assert repeated_v3_response.status_code == 201
    assert repeated_v3_response.json()["id"] == first_v3_body["id"]
    calculation_metadata = cast(
        dict[str, object],
        first_v3_body["calculationMetadata"],
    )
    assert calculation_metadata["eligibleRequirementCount"] == 2
    requirement_entries = cast(list[dict[str, object]], first_v3_body["requirements"])
    assert all(entry["requirementId"] != "" for entry in requirement_entries)
    assert all("Private manual requirement text" not in str(entry) for entry in requirement_entries)
    assert update_response.status_code == 200
    assert second_v3_response.status_code == 201
    assert second_v3_response.json()["id"] != first_v3_body["id"]
    assert second_v3_response.json()["overallScore"] == 67
    assert historic_v2_response.status_code == 200
    assert historic_v2_response.json() == v2_response.json()


def test_v3_accepts_warning_ready_cv_text_with_reviewed_requirements(client: TestClient) -> None:
    register(client, "v3-warning@example.com")
    document = upload_docx(client, "Python experience")
    version = cast(dict[str, object], document["latestVersion"])
    extraction_response = client.post(
        f"/api/v1/cv-documents/{document['id']}/versions/{version['id']}/extraction",
        headers={"X-CSRF-Token": csrf_token(client)},
    )
    target = create_job_target(client, title="Warning-ready v3 target")
    create_job_requirement(
        client,
        target_id=str(target["id"]),
        requirement="Python experience",
        category="must-have",
        normalized_skill="Python",
    )

    response = create_analysis(
        client,
        cv_document_version_id=str(version["id"]),
        job_target_id=str(target["id"]),
        scoring_version="deterministic-v3",
    )

    assert extraction_response.json()["readiness"]["state"] == "warning"
    assert response.status_code == 201
    assert response.json()["overallScore"] == 100


def test_v3_rejects_owned_targets_without_eligible_reviewed_requirements(
    client: TestClient,
) -> None:
    register(client, "v3-empty@example.com")
    _, version_id = create_ready_cv_version(client)
    target = create_job_target(client, title="No reviewed requirements")

    response = create_analysis(
        client,
        cv_document_version_id=version_id,
        job_target_id=str(target["id"]),
        scoring_version="deterministic-v3",
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "REQUIREMENTS_NOT_READY"


def test_owner_can_page_through_private_analysis_history_without_source_text(
    client: TestClient,
) -> None:
    register(client, "history@example.com")
    _, version_id = create_ready_cv_version(client)
    first_target = create_job_target(client, title="First platform target")
    second_target = create_job_target(client, title="Second platform target")
    first_analysis = cast(
        dict[str, object],
        create_analysis(
            client,
            cv_document_version_id=version_id,
            job_target_id=str(first_target["id"]),
        ).json(),
    )
    second_analysis = cast(
        dict[str, object],
        create_analysis(
            client,
            cv_document_version_id=version_id,
            job_target_id=str(second_target["id"]),
        ).json(),
    )

    first_page = client.get("/api/v1/match-analyses?limit=1")
    first_page_body = cast(dict[str, object], first_page.json())
    first_page_data = cast(list[dict[str, object]], first_page_body["data"])
    cursor = cast(str, first_page_body["nextCursor"])
    second_page = client.get(f"/api/v1/match-analyses?limit=1&cursor={cursor}")
    second_page_body = cast(dict[str, object], second_page.json())
    second_page_data = cast(list[dict[str, object]], second_page_body["data"])

    assert first_page.status_code == 200
    assert second_page.status_code == 200
    assert len(first_page_data) == 1
    assert len(second_page_data) == 1
    assert {first_page_data[0]["id"], second_page_data[0]["id"]} == {
        first_analysis["id"],
        second_analysis["id"],
    }
    assert first_page_data[0]["id"] != second_page_data[0]["id"]
    assert first_page_data[0]["cvDocumentTitle"] == "candidate-cv"
    assert {first_page_data[0]["targetTitle"], second_page_data[0]["targetTitle"]} == {
        "First platform target",
        "Second platform target",
    }
    assert second_page_body["nextCursor"] is None
    assert PRIVATE_CV_TEXT not in first_page.text
    assert "Lead the platform engineering function" not in first_page.text
    assert "cvDocumentVersionId" not in first_page.text
    assert "jobTargetId" not in first_page.text


def test_analysis_history_is_owner_scoped_and_rejects_foreign_cursors(
    client: TestClient,
    second_client: TestClient,
) -> None:
    register(client, "history-owner@example.com")
    _, owner_version_id = create_ready_cv_version(client)
    owner_target = create_job_target(client, title="Owner history target")
    owner_analysis = cast(
        dict[str, object],
        create_analysis(
            client,
            cv_document_version_id=owner_version_id,
            job_target_id=str(owner_target["id"]),
        ).json(),
    )

    register(second_client, "history-other@example.com")
    empty_history = second_client.get("/api/v1/match-analyses")
    foreign_cursor_history = second_client.get(
        f"/api/v1/match-analyses?cursor={owner_analysis['id']}"
    )

    assert empty_history.status_code == 200
    assert empty_history.json() == {"data": [], "nextCursor": None}
    assert foreign_cursor_history.status_code == 404
    assert foreign_cursor_history.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_analysis_history_requires_authentication_and_bounded_pagination(
    client: TestClient,
) -> None:
    unauthenticated_response = client.get("/api/v1/match-analyses")

    register(client, "history-bounds@example.com")
    oversized_limit_response = client.get("/api/v1/match-analyses?limit=51")
    malformed_cursor_response = client.get("/api/v1/match-analyses?cursor=not-a-uuid")

    assert unauthenticated_response.status_code == 401
    assert oversized_limit_response.status_code == 422
    assert malformed_cursor_response.status_code == 422


def test_match_analyses_are_invisible_across_owners(
    client: TestClient,
    second_client: TestClient,
) -> None:
    register(client, "owner@example.com")
    _, owner_version_id = create_ready_cv_version(client)
    owner_target = create_job_target(client, title="Owner platform target")
    owner_analysis_response = create_analysis(
        client,
        cv_document_version_id=owner_version_id,
        job_target_id=str(owner_target["id"]),
    )
    owner_analysis = cast(dict[str, object], owner_analysis_response.json())

    register(second_client, "other@example.com")
    _, other_version_id = create_ready_cv_version(second_client)
    other_target = create_job_target(second_client, title="Other platform target")
    cross_cv_response = create_analysis(
        second_client,
        cv_document_version_id=owner_version_id,
        job_target_id=str(other_target["id"]),
    )
    cross_target_response = create_analysis(
        second_client,
        cv_document_version_id=other_version_id,
        job_target_id=str(owner_target["id"]),
        scoring_version="deterministic-v3",
    )
    read_response = second_client.get(f"/api/v1/match-analyses/{owner_analysis['id']}")

    assert owner_analysis_response.status_code == 201
    assert cross_cv_response.status_code == 404
    assert cross_target_response.status_code == 404
    assert read_response.status_code == 404
    assert cross_cv_response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert cross_target_response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert read_response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_v3_rejects_client_supplied_evidence_fields(client: TestClient) -> None:
    register(client, "v3-invalid-evidence@example.com")
    _, version_id = create_ready_cv_version(client)
    target = create_job_target(client)

    response = client.post(
        "/api/v1/match-analyses",
        headers={"X-CSRF-Token": csrf_token(client)},
        json={
            "cvDocumentVersionId": version_id,
            "jobTargetId": str(target["id"]),
            "scoringVersion": "deterministic-v3",
            "evidence": [{"source": "CV_NORMALIZED_SKILL", "term": "python"}],
        },
    )

    assert response.status_code == 422
