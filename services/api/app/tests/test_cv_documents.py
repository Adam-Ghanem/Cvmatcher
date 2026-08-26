from __future__ import annotations

from io import BytesIO
from typing import cast
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi.testclient import TestClient

from app.tests.test_authentication import csrf_token, register

PDF_BYTES = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\nCVMatcher test document\n%%EOF\n"
INVALID_BYTES = b"This is not a PDF or DOCX."


def valid_docx_bytes() -> bytes:
    stream = BytesIO()
    with ZipFile(stream, mode="w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types />")
        archive.writestr("word/document.xml", "<w:document />")
    return stream.getvalue()


def upload_pdf(client: TestClient, filename: str = "candidate-cv.pdf") -> dict[str, object]:
    response = client.post(
        "/api/v1/cv-documents",
        headers={"X-CSRF-Token": csrf_token(client)},
        files={"file": (filename, BytesIO(PDF_BYTES), "application/pdf")},
    )

    assert response.status_code == 201
    return cast(dict[str, object], response.json())


def test_upload_creates_a_private_document_version_for_the_authenticated_user(
    client: TestClient,
) -> None:
    register(client, "candidate@example.com")

    document = upload_pdf(client)

    assert document["title"] == "candidate-cv"
    latest_version = cast(dict[str, object], document["latestVersion"])
    assert latest_version["versionNumber"] == 1
    assert latest_version["originalFilename"] == "candidate-cv.pdf"
    assert "storageKey" not in latest_version
    assert "file" not in document


def test_pdf_upload_rejects_extension_and_content_signature_disagreement(
    client: TestClient,
) -> None:
    register(client, "candidate@example.com")

    response = client.post(
        "/api/v1/cv-documents",
        headers={"X-CSRF-Token": csrf_token(client)},
        files={"file": ("candidate-cv.pdf", BytesIO(INVALID_BYTES), "application/pdf")},
    )

    body = cast(dict[str, object], response.json())
    error = cast(dict[str, object], body["error"])
    assert response.status_code == 422
    assert error["code"] == "UNSUPPORTED_DOCUMENT"


def test_docx_upload_requires_a_valid_office_container(client: TestClient) -> None:
    register(client, "candidate@example.com")

    response = client.post(
        "/api/v1/cv-documents",
        headers={"X-CSRF-Token": csrf_token(client)},
        files={
            "file": (
                "candidate-cv.docx",
                BytesIO(valid_docx_bytes()),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    body = cast(dict[str, object], response.json())
    latest_version = cast(dict[str, object], body["latestVersion"])
    assert response.status_code == 201
    assert latest_version["contentType"] == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


def test_path_like_original_filename_never_becomes_a_storage_identifier(client: TestClient) -> None:
    register(client, "candidate@example.com")

    document = upload_pdf(client, "../candidate-cv.pdf")

    latest_version = cast(dict[str, object], document["latestVersion"])
    assert latest_version["originalFilename"] == "candidate-cv.pdf"
    assert document["title"] == "candidate-cv"
    assert "storageKey" not in latest_version


def test_document_owner_can_create_an_immutable_second_version(client: TestClient) -> None:
    register(client, "candidate@example.com")
    document = upload_pdf(client)

    response = client.post(
        f"/api/v1/cv-documents/{document['id']}/versions",
        headers={"X-CSRF-Token": csrf_token(client)},
        files={"file": ("candidate-cv-v2.pdf", BytesIO(PDF_BYTES), "application/pdf")},
    )

    version = cast(dict[str, object], response.json())
    assert response.status_code == 201
    assert version["versionNumber"] == 2
    assert version["originalFilename"] == "candidate-cv-v2.pdf"


def test_document_is_invisible_to_a_different_authenticated_user(
    client: TestClient,
    second_client: TestClient,
) -> None:
    register(client, "owner@example.com")
    document = upload_pdf(client)
    register(second_client, "other@example.com")

    response = second_client.get(f"/api/v1/cv-documents/{document['id']}")

    body = cast(dict[str, object], response.json())
    error = cast(dict[str, object], body["error"])
    assert response.status_code == 404
    assert error["code"] == "RESOURCE_NOT_FOUND"


def test_document_list_only_returns_the_authenticated_users_documents(
    client: TestClient,
    second_client: TestClient,
) -> None:
    register(client, "owner@example.com")
    upload_pdf(client, "owner-cv.pdf")
    register(second_client, "other@example.com")
    upload_pdf(second_client, "other-cv.pdf")

    response = client.get("/api/v1/cv-documents")

    body = cast(dict[str, object], response.json())
    documents = cast(list[dict[str, object]], body["data"])
    assert response.status_code == 200
    assert [document["title"] for document in documents] == ["owner-cv"]


def test_upload_rejects_a_body_that_exceeds_the_streaming_limit(client: TestClient) -> None:
    register(client, "candidate@example.com")
    oversized_document = b"%PDF-1.7\n" + b"0" * (10 * 1024 * 1024)

    response = client.post(
        "/api/v1/cv-documents",
        headers={"X-CSRF-Token": csrf_token(client)},
        files={"file": ("oversized.pdf", BytesIO(oversized_document), "application/pdf")},
    )

    body = cast(dict[str, object], response.json())
    error = cast(dict[str, object], body["error"])
    assert response.status_code == 413
    assert error["code"] == "UPLOAD_TOO_LARGE"


def test_document_owner_can_delete_a_private_document_with_csrf(client: TestClient) -> None:
    register(client, "candidate@example.com")
    document = upload_pdf(client)

    response = client.delete(
        f"/api/v1/cv-documents/{document['id']}",
        headers={"X-CSRF-Token": csrf_token(client)},
    )
    retrieval = client.get(f"/api/v1/cv-documents/{document['id']}")

    assert response.status_code == 204
    assert retrieval.status_code == 404


def test_document_deletion_requires_csrf_and_hides_other_owners_document(
    client: TestClient,
    second_client: TestClient,
) -> None:
    register(client, "owner@example.com")
    document = upload_pdf(client)
    csrf_response = client.delete(f"/api/v1/cv-documents/{document['id']}")

    register(second_client, "other@example.com")
    cross_owner_response = second_client.delete(
        f"/api/v1/cv-documents/{document['id']}",
        headers={"X-CSRF-Token": csrf_token(second_client)},
    )

    assert csrf_response.status_code == 403
    assert cross_owner_response.status_code == 404
    assert cross_owner_response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
