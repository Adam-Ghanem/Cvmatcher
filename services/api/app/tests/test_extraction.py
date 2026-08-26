from __future__ import annotations

from io import BytesIO
from typing import cast
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.services.cv_extraction import (
    MAX_EXTRACTED_CHARACTERS,
    ExtractionWorkerError,
    extract_text_in_child_process,
    join_bounded_text,
)
from app.services.object_storage import DOCX_MIME_TYPE, PDF_MIME_TYPE
from app.tests.test_authentication import csrf_token, register
from app.tests.test_cv_documents import upload_pdf


def test_owner_can_extract_a_saved_cv_version_without_receiving_raw_text(
    client: TestClient,
) -> None:
    register(client, "candidate@example.com")
    document = upload_pdf(client)
    version = cast(dict[str, object], document["latestVersion"])

    response = client.post(
        f"/api/v1/cv-documents/{document['id']}/versions/{version['id']}/extraction",
        headers={"X-CSRF-Token": csrf_token(client)},
    )

    body = cast(dict[str, object], response.json())
    assert response.status_code == 200
    assert body["status"] == "failed"
    assert body["sourceType"] == "pdf"
    assert body["characterCount"] == 0
    assert "text" not in body


def test_extraction_is_invisible_to_a_different_user(
    client: TestClient,
    second_client: TestClient,
) -> None:
    register(client, "owner@example.com")
    document = upload_pdf(client)
    version = cast(dict[str, object], document["latestVersion"])
    register(second_client, "other@example.com")

    response = second_client.post(
        f"/api/v1/cv-documents/{document['id']}/versions/{version['id']}/extraction",
        headers={"X-CSRF-Token": csrf_token(second_client)},
    )

    body = cast(dict[str, object], response.json())
    error = cast(dict[str, object], body["error"])
    assert response.status_code == 404
    assert error["code"] == "RESOURCE_NOT_FOUND"


def valid_docx_payload(body_text: str) -> bytes:
    payload = BytesIO()
    with ZipFile(payload, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types />")
        archive.writestr(
            "word/document.xml",
            "<w:document xmlns:w='urn:test'><w:body><w:p><w:r><w:t>"
            f"{body_text}</w:t></w:r></w:p></w:body></w:document>",
        )
    return payload.getvalue()


def valid_pdf_payload(page_count: int = 1, *, encrypted: bool = False) -> bytes:
    payload = BytesIO()
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=612, height=792)
    if encrypted:
        writer.encrypt("test-only-password")
    writer.write(payload)
    return payload.getvalue()


def docx_payload_with_extra_entries(extra_entries: int) -> bytes:
    payload = BytesIO()
    with ZipFile(payload, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types />")
        archive.writestr("word/document.xml", "<w:document xmlns:w='urn:test' />")
        for entry_index in range(extra_entries):
            archive.writestr(f"word/media/{entry_index}.bin", b"x")
    return payload.getvalue()


def upload_docx(client: TestClient, body_text: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/cv-documents",
        headers={"X-CSRF-Token": csrf_token(client)},
        files={
            "file": (
                "candidate-cv.docx",
                BytesIO(valid_docx_payload(body_text)),
                DOCX_MIME_TYPE,
            )
        },
    )

    assert response.status_code == 201
    return cast(dict[str, object], response.json())


def test_bounded_child_process_extracts_valid_pdf() -> None:
    source_type, extracted_text = extract_text_in_child_process(
        valid_pdf_payload(),
        PDF_MIME_TYPE,
    )

    assert source_type == "pdf"
    assert extracted_text == ""


def test_bounded_child_process_rejects_excessive_pdf_page_count() -> None:
    with pytest.raises(ExtractionWorkerError):
        extract_text_in_child_process(valid_pdf_payload(page_count=101), PDF_MIME_TYPE)


def test_bounded_child_process_rejects_encrypted_pdf() -> None:
    with pytest.raises(ExtractionWorkerError):
        extract_text_in_child_process(valid_pdf_payload(encrypted=True), PDF_MIME_TYPE)


def test_bounded_child_process_revalidates_docx_archive_entry_limit() -> None:
    with pytest.raises(ExtractionWorkerError):
        extract_text_in_child_process(
            docx_payload_with_extra_entries(2_000),
            DOCX_MIME_TYPE,
        )


def test_bounded_child_process_rejects_docx_doctype_declarations() -> None:
    with pytest.raises(ExtractionWorkerError):
        extract_text_in_child_process(
            valid_docx_payload("<!DOCTYPE candidate>"),
            DOCX_MIME_TYPE,
        )


def test_text_joining_stops_at_the_private_character_limit() -> None:
    extracted_text = join_bounded_text(["a" * MAX_EXTRACTED_CHARACTERS, "later"])

    assert len(extracted_text) == MAX_EXTRACTED_CHARACTERS
    assert extracted_text.endswith("a")


def test_bounded_child_process_extracts_docx_body_text() -> None:
    source_type, extracted_text = extract_text_in_child_process(
        valid_docx_payload("Senior platform engineer"),
        DOCX_MIME_TYPE,
    )

    assert source_type == "docx"
    assert extracted_text == "Senior platform engineer"


def test_owner_can_extract_valid_docx_without_receiving_private_text(client: TestClient) -> None:
    register(client, "candidate@example.com")
    document = upload_docx(client, "Private CV content")
    version = cast(dict[str, object], document["latestVersion"])

    response = client.post(
        f"/api/v1/cv-documents/{document['id']}/versions/{version['id']}/extraction",
        headers={"X-CSRF-Token": csrf_token(client)},
    )

    body = cast(dict[str, object], response.json())
    assert response.status_code == 200
    assert body["status"] == "succeeded"
    assert body["sourceType"] == "docx"
    assert body["characterCount"] == len("Private CV content")
    assert "text" not in body
    assert "Private CV content" not in response.text


def test_extraction_status_can_be_retrieved_without_reprocessing(client: TestClient) -> None:
    register(client, "candidate@example.com")
    document = upload_docx(client, "Private CV content")
    version = cast(dict[str, object], document["latestVersion"])
    extraction_url = (
        f"/api/v1/cv-documents/{document['id']}/versions/{version['id']}/extraction"
    )
    headers = {"X-CSRF-Token": csrf_token(client)}

    created_response = client.post(extraction_url, headers=headers)
    retrieved_response = client.get(extraction_url)

    created_body = cast(dict[str, object], created_response.json())
    retrieved_body = cast(dict[str, object], retrieved_response.json())
    assert created_response.status_code == 200
    assert retrieved_response.status_code == 200
    assert retrieved_body == created_body
    assert "Private CV content" not in retrieved_response.text


def test_repeating_successful_extraction_reuses_the_existing_record(client: TestClient) -> None:
    register(client, "candidate@example.com")
    document = upload_docx(client, "Private CV content")
    version = cast(dict[str, object], document["latestVersion"])
    extraction_url = (
        f"/api/v1/cv-documents/{document['id']}/versions/{version['id']}/extraction"
    )
    headers = {"X-CSRF-Token": csrf_token(client)}

    first_response = client.post(extraction_url, headers=headers)
    second_response = client.post(extraction_url, headers=headers)

    first_body = cast(dict[str, object], first_response.json())
    second_body = cast(dict[str, object], second_response.json())
    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_body["id"] == second_body["id"]
    assert second_body["status"] == "succeeded"


def test_extraction_quality_assessment_reports_only_bounded_non_content_metadata() -> None:
    from app.services.cv_extraction import assess_extracted_text

    assessment = assess_extracted_text("Candidate\nPython\nExperience")

    assert assessment.character_count == len("Candidate\nPython\nExperience")
    assert assessment.line_count == 3
    assert assessment.quality == "usable"
    assert assessment.warnings == ()


def test_extraction_quality_assessment_warns_when_document_contains_no_extractable_text() -> None:
    from app.services.cv_extraction import assess_extracted_text

    assessment = assess_extracted_text("")

    assert assessment.character_count == 0
    assert assessment.line_count == 0
    assert assessment.quality == "low"
    assert assessment.warnings == ("NO_EXTRACTABLE_TEXT",)


def test_successful_extraction_returns_safe_parser_and_quality_metadata(client: TestClient) -> None:
    register(client, "metadata@example.com")
    document = upload_docx(client, "Private CV content")
    version = cast(dict[str, object], document["latestVersion"])

    response = client.post(
        f"/api/v1/cv-documents/{document['id']}/versions/{version['id']}/extraction",
        headers={"X-CSRF-Token": csrf_token(client)},
    )

    body = cast(dict[str, object], response.json())
    assert response.status_code == 200
    assert body["parserVersion"] == "bounded-text-v2"
    assert body["quality"] == "usable"
    assert body["warnings"] == []
    assert "Private CV content" not in response.text
