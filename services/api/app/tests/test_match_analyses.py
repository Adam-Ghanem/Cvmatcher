from __future__ import annotations

from typing import cast
from uuid import uuid4

from fastapi.testclient import TestClient
from httpx import Response

from app.tests.test_authentication import csrf_token, register
from app.tests.test_extraction import upload_docx
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
) -> Response:
    headers = {"X-CSRF-Token": csrf_token(client)} if include_csrf else {}

    return cast(
        Response,
        client.post(
            "/api/v1/match-analyses",
            headers=headers,
            json={
                "cvDocumentVersionId": cv_document_version_id,
                "jobTargetId": job_target_id,
            },
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
    )
    read_response = second_client.get(f"/api/v1/match-analyses/{owner_analysis['id']}")

    assert owner_analysis_response.status_code == 201
    assert cross_cv_response.status_code == 404
    assert cross_target_response.status_code == 404
    assert read_response.status_code == 404
    assert cross_cv_response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert cross_target_response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert read_response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
