from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Header, Request, UploadFile, status

from app.api.dependencies import AuthenticatedSessionDependency, DatabaseSession
from app.core.config import Settings
from app.schemas.cv_documents import (
    CvDocumentListResponse,
    CvDocumentSummary,
    CvDocumentVersionsResponse,
    CvDocumentVersionSummary,
)
from app.services.authentication import CSRF_COOKIE_NAME, require_csrf_token
from app.services.cv_documents import CvDocumentService
from app.services.object_storage import PrivateObjectStorage

router = APIRouter(prefix="/cv-documents", tags=["cv documents"])


def document_service(request: Request) -> CvDocumentService:
    storage: PrivateObjectStorage = request.app.state.object_storage
    return CvDocumentService(storage)


def validate_authenticated_csrf(
    request: Request,
    *,
    authenticated_session: AuthenticatedSessionDependency,
    submitted_csrf_token: str | None,
) -> None:
    settings: Settings = request.app.state.settings
    require_csrf_token(
        submitted_token=submitted_csrf_token,
        cookie_token=request.cookies.get(CSRF_COOKIE_NAME),
        authenticated_session=authenticated_session,
        settings=settings,
    )


@router.get("", response_model=CvDocumentListResponse)
async def list_cv_documents(
    request: Request,
    database_session: DatabaseSession,
    authenticated_session: AuthenticatedSessionDependency,
) -> CvDocumentListResponse:
    documents = await document_service(request).list_documents(
        database_session,
        user_id=authenticated_session.principal.user_id,
    )
    return CvDocumentListResponse(data=documents)


@router.post("", response_model=CvDocumentSummary, status_code=status.HTTP_201_CREATED)
async def create_cv_document(
    request: Request,
    database_session: DatabaseSession,
    authenticated_session: AuthenticatedSessionDependency,
    file: Annotated[UploadFile, File(description="A PDF or DOCX CV document")],
    submitted_csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> CvDocumentSummary:
    validate_authenticated_csrf(
        request,
        authenticated_session=authenticated_session,
        submitted_csrf_token=submitted_csrf_token,
    )
    settings: Settings = request.app.state.settings
    storage: PrivateObjectStorage = request.app.state.object_storage
    staged_document = await storage.stage_upload(file, max_bytes=settings.max_upload_bytes)
    try:
        return await document_service(request).create_document(
            database_session,
            user_id=authenticated_session.principal.user_id,
            staged_document=staged_document,
        )
    except Exception:
        await storage.discard_staged(staged_document)
        raise


@router.get("/{document_id}", response_model=CvDocumentSummary)
async def get_cv_document(
    document_id: UUID,
    request: Request,
    database_session: DatabaseSession,
    authenticated_session: AuthenticatedSessionDependency,
) -> CvDocumentSummary:
    return await document_service(request).get_document(
        database_session,
        document_id=document_id,
        user_id=authenticated_session.principal.user_id,
    )


@router.get("/{document_id}/versions", response_model=CvDocumentVersionsResponse)
async def list_cv_document_versions(
    document_id: UUID,
    request: Request,
    database_session: DatabaseSession,
    authenticated_session: AuthenticatedSessionDependency,
) -> CvDocumentVersionsResponse:
    versions = await document_service(request).list_versions(
        database_session,
        document_id=document_id,
        user_id=authenticated_session.principal.user_id,
    )
    return CvDocumentVersionsResponse(data=versions)


@router.post(
    "/{document_id}/versions",
    response_model=CvDocumentVersionSummary,
    status_code=status.HTTP_201_CREATED,
)
async def create_cv_document_version(
    document_id: UUID,
    request: Request,
    database_session: DatabaseSession,
    authenticated_session: AuthenticatedSessionDependency,
    file: Annotated[UploadFile, File(description="A PDF or DOCX CV document")],
    submitted_csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> CvDocumentVersionSummary:
    validate_authenticated_csrf(
        request,
        authenticated_session=authenticated_session,
        submitted_csrf_token=submitted_csrf_token,
    )
    settings: Settings = request.app.state.settings
    storage: PrivateObjectStorage = request.app.state.object_storage
    staged_document = await storage.stage_upload(file, max_bytes=settings.max_upload_bytes)
    try:
        return await document_service(request).add_version(
            database_session,
            document_id=document_id,
            user_id=authenticated_session.principal.user_id,
            staged_document=staged_document,
        )
    except Exception:
        await storage.discard_staged(staged_document)
        raise
