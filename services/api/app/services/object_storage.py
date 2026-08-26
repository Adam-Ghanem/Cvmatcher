from __future__ import annotations

import hashlib
import os
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Protocol
from uuid import uuid4

from fastapi import UploadFile

from app.core.errors import ApiException

PDF_MIME_TYPE = "application/pdf"
DOCX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
ALLOWED_CONTENT_TYPES = frozenset({PDF_MIME_TYPE, DOCX_MIME_TYPE})
STREAM_CHUNK_SIZE = 64 * 1024
MAX_DOCX_ARCHIVE_ENTRIES = 2_000
MAX_DOCX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class PrivateObjectKey:
    """Opaque server-generated storage identifier. It must never contain client path data."""

    value: str


@dataclass(slots=True)
class StagedDocument:
    staging_path: Path
    original_filename: str
    content_type: str
    byte_size: int
    sha256_digest: str


class PrivateObjectStorage(Protocol):
    """Server-only sensitive document storage contract."""

    async def stage_upload(self, upload: UploadFile, *, max_bytes: int) -> StagedDocument: ...

    async def commit_staged(self, staged_document: StagedDocument) -> PrivateObjectKey: ...

    async def delete(self, *, object_key: PrivateObjectKey) -> None: ...

    async def discard_staged(self, staged_document: StagedDocument) -> None: ...


def safe_original_filename(value: str | None) -> str:
    raw_name = (value or "").replace("\\", "/")
    name = PurePosixPath(raw_name).name.strip()
    if not name or name in {".", ".."} or any(ord(character) < 32 for character in name):
        raise ApiException(
            code="UNSUPPORTED_DOCUMENT",
            message="Choose a valid PDF or DOCX file and try again.",
            status_code=422,
        )
    return name[:255]


def validate_document_signature(
    *,
    filename: str,
    declared_content_type: str | None,
    staging_path: Path,
) -> str:
    extension = Path(filename).suffix.casefold()
    content_type = (declared_content_type or "").split(";", maxsplit=1)[0].strip().casefold()
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ApiException(
            code="UNSUPPORTED_DOCUMENT",
            message="Only PDF and DOCX CV files are supported.",
            status_code=422,
        )

    with staging_path.open("rb") as staged_file:
        signature = staged_file.read(8)

    if extension == ".pdf" and content_type == PDF_MIME_TYPE and signature.startswith(b"%PDF-"):
        return PDF_MIME_TYPE
    if (
        extension == ".docx"
        and content_type == DOCX_MIME_TYPE
        and signature.startswith(b"PK\x03\x04")
    ):
        validate_docx_container(staging_path)
        return DOCX_MIME_TYPE

    raise ApiException(
        code="UNSUPPORTED_DOCUMENT",
        message=(
            "The file extension, declared type, and document signature must match a PDF or DOCX CV."
        ),
        status_code=422,
    )


def validate_docx_container(staging_path: Path) -> None:
    try:
        with zipfile.ZipFile(staging_path) as archive:
            file_infos = archive.infolist()
            if len(file_infos) > MAX_DOCX_ARCHIVE_ENTRIES:
                raise ValueError("too many archive entries")
            if sum(file_info.file_size for file_info in file_infos) > MAX_DOCX_UNCOMPRESSED_BYTES:
                raise ValueError("archive expansion exceeds policy")
            names = {file_info.filename for file_info in file_infos}
            if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                raise ValueError("required Office markers absent")
            if any(
                PurePosixPath(file_info.filename).is_absolute()
                or ".." in PurePosixPath(file_info.filename).parts
                for file_info in file_infos
            ):
                raise ValueError("unsafe archive member path")
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        raise ApiException(
            code="UNSUPPORTED_DOCUMENT",
            message="The DOCX file is not a supported Office document.",
            status_code=422,
        ) from exc


class LocalPrivateObjectStorage:
    """Private filesystem storage for development/test. It has no public-serving capability."""

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()
        self._object_root = self._root / "objects"
        self._staging_root = self._root / "staging"
        for directory in (self._object_root, self._staging_root):
            directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            directory.chmod(0o700)

    async def stage_upload(self, upload: UploadFile, *, max_bytes: int) -> StagedDocument:
        original_filename = safe_original_filename(upload.filename)
        descriptor, temporary_name = tempfile.mkstemp(prefix="upload-", dir=self._staging_root)
        staging_path = Path(temporary_name)
        os.fchmod(descriptor, 0o600)
        byte_size = 0
        digest = hashlib.sha256()
        try:
            with os.fdopen(descriptor, "wb") as temporary_file:
                while chunk := await upload.read(STREAM_CHUNK_SIZE):
                    byte_size += len(chunk)
                    if byte_size > max_bytes:
                        raise ApiException(
                            code="UPLOAD_TOO_LARGE",
                            message="This CV is larger than the 10 MiB upload limit.",
                            status_code=413,
                        )
                    digest.update(chunk)
                    temporary_file.write(chunk)
            if byte_size == 0:
                raise ApiException(
                    code="UNSUPPORTED_DOCUMENT",
                    message="Choose a non-empty PDF or DOCX CV and try again.",
                    status_code=422,
                )
            content_type = validate_document_signature(
                filename=original_filename,
                declared_content_type=upload.content_type,
                staging_path=staging_path,
            )
            return StagedDocument(
                staging_path=staging_path,
                original_filename=original_filename,
                content_type=content_type,
                byte_size=byte_size,
                sha256_digest=digest.hexdigest(),
            )
        except Exception:
            staging_path.unlink(missing_ok=True)
            raise
        finally:
            await upload.close()

    async def commit_staged(self, staged_document: StagedDocument) -> PrivateObjectKey:
        object_key = PrivateObjectKey(value=f"cv/{uuid4().hex}")
        destination = self._object_path(object_key)
        destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        destination.parent.chmod(0o700)
        try:
            os.replace(staged_document.staging_path, destination)
            destination.chmod(0o600)
        except OSError as exc:
            staged_document.staging_path.unlink(missing_ok=True)
            raise ApiException(
                code="DOCUMENT_STORAGE_FAILED",
                message="We could not store this CV. Please try again.",
                status_code=503,
            ) from exc
        return object_key

    async def delete(self, *, object_key: PrivateObjectKey) -> None:
        self._object_path(object_key).unlink(missing_ok=True)

    async def discard_staged(self, staged_document: StagedDocument) -> None:
        staged_document.staging_path.unlink(missing_ok=True)

    def _object_path(self, object_key: PrivateObjectKey) -> Path:
        key_path = PurePosixPath(object_key.value)
        if key_path.is_absolute() or ".." in key_path.parts:
            raise ValueError("Object key must be a safe relative identifier.")
        candidate = (self._object_root / Path(*key_path.parts)).resolve()
        if self._object_root not in candidate.parents:
            raise ValueError("Object key escapes private storage root.")
        return candidate
