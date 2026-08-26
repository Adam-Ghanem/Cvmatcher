from __future__ import annotations

import asyncio
import contextlib
import io
import multiprocessing
import sys
import time
import xml.etree.ElementTree as element_tree
import zipfile
from collections.abc import Iterable
from datetime import UTC, datetime
from multiprocessing.connection import Connection
from typing import Final, Protocol
from uuid import UUID

from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiException
from app.models.cv_document import CvDocument, CvDocumentVersion
from app.models.cv_extraction import CvExtraction
from app.services.object_storage import (
    DOCX_MIME_TYPE,
    PDF_MIME_TYPE,
    PrivateObjectKey,
    PrivateObjectStorage,
    validate_docx_archive,
)

MAX_PDF_PAGES: Final = 100
MAX_EXTRACTED_CHARACTERS: Final = 250_000
EXTRACTION_WALL_TIMEOUT_SECONDS: Final = 8.0
EXTRACTION_CPU_LIMIT_SECONDS: Final = 4
EXTRACTION_ADDRESS_SPACE_BYTES: Final = 256 * 1024 * 1024
_WORKER_POLL_INTERVAL_SECONDS: Final = 0.05
_WORKER_SHUTDOWN_GRACE_SECONDS: Final = 0.25
SAFE_FAILURE_MESSAGE: Final = (
    "We could not read this CV. Upload a different PDF or DOCX and try again."
)


class ExtractionWorkerError(Exception):
    """Raised when the constrained extraction worker cannot produce a safe result."""


class ManagedExtractionProcess(Protocol):
    def start(self) -> None: ...

    def is_alive(self) -> bool: ...

    def join(self, timeout: float | None = None) -> None: ...

    def terminate(self) -> None: ...

    def kill(self) -> None: ...

    def close(self) -> None: ...


async def get_owned_extraction(
    database_session: AsyncSession,
    *,
    user_id: UUID,
    document_id: UUID,
    version_id: UUID,
) -> CvExtraction:
    extraction = await database_session.scalar(
        select(CvExtraction)
        .join(CvDocumentVersion, CvDocumentVersion.id == CvExtraction.document_version_id)
        .join(CvDocument, CvDocument.id == CvDocumentVersion.document_id)
        .where(
            CvDocument.id == document_id,
            CvDocument.user_id == user_id,
            CvDocumentVersion.id == version_id,
        )
    )
    if extraction is None:
        raise ApiException("RESOURCE_NOT_FOUND", "We could not find that CV extraction.", 404)
    return extraction


async def extract_owned_version(
    database_session: AsyncSession,
    storage: PrivateObjectStorage,
    *,
    user_id: UUID,
    document_id: UUID,
    version_id: UUID,
    max_upload_bytes: int,
) -> CvExtraction:
    result = await database_session.execute(
        select(CvDocumentVersion)
        .join(CvDocument, CvDocument.id == CvDocumentVersion.document_id)
        .where(
            CvDocument.id == document_id,
            CvDocument.user_id == user_id,
            CvDocumentVersion.id == version_id,
        )
        .with_for_update()
    )
    version = result.scalar_one_or_none()
    if version is None:
        raise ApiException("RESOURCE_NOT_FOUND", "We could not find that CV document.", 404)

    extraction = await database_session.scalar(
        select(CvExtraction).where(CvExtraction.document_version_id == version.id)
    )
    if extraction is not None and extraction.status == "succeeded":
        return extraction

    source_type = source_type_for_content_type(version.content_type)
    if extraction is None:
        extraction = CvExtraction(
            document_version_id=version.id,
            status="processing",
            source_type=source_type,
        )
        database_session.add(extraction)
    else:
        extraction.status = "processing"
        extraction.source_type = source_type
        extraction.character_count = 0
        extraction.extracted_text = None
        extraction.failure_message = None
        extraction.completed_at = None
    await database_session.flush()

    try:
        payload = await storage.read_bytes(
            object_key=PrivateObjectKey(version.private_object_key),
            max_bytes=max_upload_bytes,
        )
        extracted_source_type, text = await asyncio.to_thread(
            extract_text_in_child_process,
            payload,
            version.content_type,
        )
    except (ApiException, ExtractionWorkerError, OSError):
        mark_extraction_failed(extraction)
    else:
        extraction.status = "succeeded"
        extraction.source_type = extracted_source_type
        extraction.extracted_text = text
        extraction.character_count = len(text)
        extraction.failure_message = None
        extraction.completed_at = datetime.now(UTC)

    await database_session.flush()
    await database_session.refresh(extraction)
    return extraction


def source_type_for_content_type(content_type: str) -> str:
    if content_type == PDF_MIME_TYPE:
        return "pdf"
    if content_type == DOCX_MIME_TYPE:
        return "docx"
    raise ExtractionWorkerError("Unsupported stored document type.")


def mark_extraction_failed(extraction: CvExtraction) -> None:
    extraction.status = "failed"
    extraction.character_count = 0
    extraction.extracted_text = None
    extraction.failure_message = SAFE_FAILURE_MESSAGE
    extraction.completed_at = datetime.now(UTC)


def extract_text_in_child_process(payload: bytes, content_type: str) -> tuple[str, str]:
    """Run untrusted document parsing outside the API process with bounded resources."""
    context = multiprocessing.get_context("spawn")
    parent_connection, child_connection = context.Pipe(duplex=False)
    process: ManagedExtractionProcess = context.Process(
        target=_extraction_worker_entry,
        args=(payload, content_type, child_connection),
        daemon=True,
    )
    try:
        process.start()
        child_connection.close()
        return receive_worker_result(process, parent_connection)
    except (OSError, ValueError) as exc:
        raise ExtractionWorkerError("Unable to start extraction worker.") from exc
    finally:
        child_connection.close()
        parent_connection.close()
        stop_worker_process(process)


def receive_worker_result(
    process: ManagedExtractionProcess,
    parent_connection: Connection,
) -> tuple[str, str]:
    deadline = time.monotonic() + EXTRACTION_WALL_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        if parent_connection.poll(min(_WORKER_POLL_INTERVAL_SECONDS, remaining)):
            try:
                succeeded, source_type, text = parent_connection.recv()
            except (EOFError, OSError) as exc:
                raise ExtractionWorkerError("Extraction worker ended without a result.") from exc
            if not succeeded:
                raise ExtractionWorkerError("Document parser rejected the file.")
            return source_type, text
        if not process.is_alive():
            process.join(timeout=_WORKER_SHUTDOWN_GRACE_SECONDS)
            raise ExtractionWorkerError("Extraction worker ended without a result.")
    raise ExtractionWorkerError("Extraction worker exceeded the wall-clock limit.")


def stop_worker_process(process: ManagedExtractionProcess) -> None:
    if process.is_alive():
        process.terminate()
        process.join(timeout=_WORKER_SHUTDOWN_GRACE_SECONDS)
    if process.is_alive():
        process.kill()
        process.join(timeout=_WORKER_SHUTDOWN_GRACE_SECONDS)
    process.close()


def _extraction_worker_entry(
    payload: bytes,
    content_type: str,
    child_connection: Connection,
) -> None:
    try:
        apply_linux_resource_limits()
        source_type, text = extract_text(payload, content_type)
        child_connection.send((True, source_type, text))
    except BaseException:
        with contextlib.suppress(BrokenPipeError, OSError):
            child_connection.send((False, "", ""))
    finally:
        child_connection.close()


def apply_linux_resource_limits() -> None:
    if not sys.platform.startswith("linux"):
        return
    import resource

    resource.setrlimit(
        resource.RLIMIT_CPU,
        (EXTRACTION_CPU_LIMIT_SECONDS, EXTRACTION_CPU_LIMIT_SECONDS),
    )
    resource.setrlimit(
        resource.RLIMIT_AS,
        (EXTRACTION_ADDRESS_SPACE_BYTES, EXTRACTION_ADDRESS_SPACE_BYTES),
    )


def extract_text(payload: bytes, content_type: str) -> tuple[str, str]:
    if content_type == PDF_MIME_TYPE:
        return "pdf", extract_pdf_text(payload)
    if content_type == DOCX_MIME_TYPE:
        return "docx", extract_docx_text(payload)
    raise ExtractionWorkerError("Unsupported stored document type.")


def extract_pdf_text(payload: bytes) -> str:
    reader = PdfReader(io.BytesIO(payload), strict=False)
    if reader.is_encrypted:
        raise ExtractionWorkerError("Encrypted PDFs are not supported.")
    if len(reader.pages) > MAX_PDF_PAGES:
        raise ExtractionWorkerError("PDF page limit exceeded.")
    return join_bounded_text(page.extract_text() or "" for page in reader.pages)


def extract_docx_text(payload: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        validate_docx_archive(archive)
        xml_payload = archive.read("word/document.xml")
    if b"<!DOCTYPE" in xml_payload.upper() or b"<!ENTITY" in xml_payload.upper():
        raise ExtractionWorkerError("XML declarations are not supported.")
    root = element_tree.fromstring(xml_payload)
    return join_bounded_text(
        node.text or "" for node in root.iter() if node.tag.endswith("}t")
    )


def join_bounded_text(parts: Iterable[str]) -> str:
    remaining = MAX_EXTRACTED_CHARACTERS
    chunks: list[str] = []
    for part in parts:
        value = str(part)
        if not value:
            continue
        if chunks:
            if remaining == 0:
                break
            chunks.append("\n")
            remaining -= 1
        if remaining == 0:
            break
        chunks.append(value[:remaining])
        remaining -= min(len(value), remaining)
    return "".join(chunks)
