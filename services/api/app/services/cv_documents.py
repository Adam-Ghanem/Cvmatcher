from __future__ import annotations

from pathlib import Path
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiException
from app.models.cv_document import CvDocument, CvDocumentVersion
from app.schemas.cv_documents import (
    CvDocumentSummary,
    CvDocumentVersionSummary,
)
from app.services.object_storage import PrivateObjectKey, PrivateObjectStorage, StagedDocument


def version_summary(version: CvDocumentVersion) -> CvDocumentVersionSummary:
    return CvDocumentVersionSummary(
        id=version.id,
        version_number=version.version_number,
        original_filename=version.original_filename,
        content_type=version.content_type,
        byte_size=version.byte_size,
        uploaded_at=version.uploaded_at,
    )


def document_summary(document: CvDocument, version: CvDocumentVersion) -> CvDocumentSummary:
    return CvDocumentSummary(
        id=document.id,
        title=document.title,
        created_at=document.created_at,
        updated_at=document.updated_at,
        latest_version=version_summary(version),
    )


def document_title(filename: str) -> str:
    title = Path(filename).stem.strip()
    return title[:180] or "Untitled CV"


class CvDocumentService:
    def __init__(self, storage: PrivateObjectStorage) -> None:
        self._storage = storage

    async def create_document(
        self,
        database_session: AsyncSession,
        *,
        user_id: UUID,
        staged_document: StagedDocument,
    ) -> CvDocumentSummary:
        document = CvDocument(
            user_id=user_id, title=document_title(staged_document.original_filename)
        )
        database_session.add(document)
        await database_session.flush()
        object_key = await self._storage.commit_staged(staged_document)
        version = CvDocumentVersion(
            document_id=document.id,
            version_number=1,
            original_filename=staged_document.original_filename,
            content_type=staged_document.content_type,
            byte_size=staged_document.byte_size,
            sha256_digest=staged_document.sha256_digest,
            private_object_key=object_key.value,
        )
        database_session.add(version)
        try:
            await database_session.commit()
            await database_session.refresh(document)
            await database_session.refresh(version)
        except Exception:
            await database_session.rollback()
            await self._storage.delete(object_key=object_key)
            raise
        return document_summary(document, version)

    async def add_version(
        self,
        database_session: AsyncSession,
        *,
        document_id: UUID,
        user_id: UUID,
        staged_document: StagedDocument,
    ) -> CvDocumentVersionSummary:
        document = await database_session.scalar(
            select(CvDocument)
            .where(CvDocument.id == document_id, CvDocument.user_id == user_id)
            .with_for_update()
        )
        if document is None:
            await self._storage.discard_staged(staged_document)
            raise self._not_found_error()

        latest_version_number = await database_session.scalar(
            select(func.max(CvDocumentVersion.version_number)).where(
                CvDocumentVersion.document_id == document.id
            )
        )
        object_key = await self._storage.commit_staged(staged_document)
        version = CvDocumentVersion(
            document_id=document.id,
            version_number=(latest_version_number or 0) + 1,
            original_filename=staged_document.original_filename,
            content_type=staged_document.content_type,
            byte_size=staged_document.byte_size,
            sha256_digest=staged_document.sha256_digest,
            private_object_key=object_key.value,
        )
        database_session.add(version)
        try:
            await database_session.commit()
            await database_session.refresh(version)
        except Exception:
            await database_session.rollback()
            await self._storage.delete(object_key=object_key)
            raise
        return version_summary(version)

    async def delete_document(
        self,
        database_session: AsyncSession,
        *,
        document_id: UUID,
        user_id: UUID,
    ) -> None:
        document = await database_session.scalar(
            select(CvDocument)
            .where(CvDocument.id == document_id, CvDocument.user_id == user_id)
            .with_for_update()
        )
        if document is None:
            raise self._not_found_error()
        versions = await database_session.scalars(
            select(CvDocumentVersion.private_object_key).where(
                CvDocumentVersion.document_id == document.id
            )
        )
        for object_key in versions:
            await self._storage.delete(object_key=PrivateObjectKey(value=object_key))
        await database_session.delete(document)
        await database_session.flush()

    async def get_document(
        self,
        database_session: AsyncSession,
        *,
        document_id: UUID,
        user_id: UUID,
    ) -> CvDocumentSummary:
        statement = self._latest_document_statement().where(
            CvDocument.id == document_id,
            CvDocument.user_id == user_id,
        )
        row = (await database_session.execute(statement)).one_or_none()
        if row is None:
            raise self._not_found_error()
        return document_summary(row.CvDocument, row.CvDocumentVersion)

    async def list_versions(
        self,
        database_session: AsyncSession,
        *,
        document_id: UUID,
        user_id: UUID,
    ) -> list[CvDocumentVersionSummary]:
        document = await database_session.scalar(
            select(CvDocument.id).where(
                CvDocument.id == document_id,
                CvDocument.user_id == user_id,
            )
        )
        if document is None:
            raise self._not_found_error()
        result = await database_session.execute(
            select(CvDocumentVersion)
            .where(CvDocumentVersion.document_id == document_id)
            .order_by(CvDocumentVersion.version_number.desc())
        )
        return [version_summary(version) for version in result.scalars()]

    async def list_documents(
        self,
        database_session: AsyncSession,
        *,
        user_id: UUID,
    ) -> list[CvDocumentSummary]:
        result = await database_session.execute(
            self._latest_document_statement()
            .where(CvDocument.user_id == user_id)
            .order_by(CvDocument.updated_at.desc(), CvDocument.id.desc())
        )
        return [document_summary(row.CvDocument, row.CvDocumentVersion) for row in result.all()]

    @staticmethod
    def _latest_document_statement() -> Select[tuple[CvDocument, CvDocumentVersion]]:
        latest_versions = (
            select(
                CvDocumentVersion.document_id,
                func.max(CvDocumentVersion.version_number).label("latest_version_number"),
            )
            .group_by(CvDocumentVersion.document_id)
            .subquery()
        )
        return (
            select(CvDocument, CvDocumentVersion)
            .join(latest_versions, latest_versions.c.document_id == CvDocument.id)
            .join(
                CvDocumentVersion,
                (CvDocumentVersion.document_id == latest_versions.c.document_id)
                & (CvDocumentVersion.version_number == latest_versions.c.latest_version_number),
            )
        )

    @staticmethod
    def _not_found_error() -> ApiException:
        return ApiException(
            code="RESOURCE_NOT_FOUND",
            message="We could not find that CV document.",
            status_code=404,
        )
