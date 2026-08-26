from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Header, Request

from app.api.dependencies import AuthenticatedSessionDependency, DatabaseSession
from app.core.config import Settings
from app.models.cv_extraction import CvExtraction
from app.schemas.extraction import CvExtractionReadinessResponse, CvExtractionResponse
from app.services.authentication import CSRF_COOKIE_NAME, require_csrf_token
from app.services.cv_extraction import derive_readiness, extract_owned_version, get_owned_extraction
from app.services.object_storage import PrivateObjectStorage

router = APIRouter(tags=["cv extraction"])


def extraction_response(extraction: CvExtraction) -> CvExtractionResponse:
    readiness = derive_readiness(
        status=extraction.status,
        quality=extraction.quality,
        warnings=extraction.warnings,
    )
    return CvExtractionResponse(
        id=extraction.id,
        status=extraction.status,
        source_type=extraction.source_type,
        character_count=extraction.character_count,
        parser_version=extraction.parser_version,
        quality=extraction.quality,
        warnings=list(readiness.warnings),
        readiness=CvExtractionReadinessResponse(
            state=readiness.state,
            explanation=readiness.explanation,
            recovery_guidance=readiness.recovery_guidance,
        ),
        completed_at=extraction.completed_at,
        failure_message=extraction.failure_message,
    )


@router.get(
    "/cv-documents/{document_id}/versions/{version_id}/extraction",
    response_model=CvExtractionResponse,
)
async def read_extraction(
    document_id: UUID,
    version_id: UUID,
    database_session: DatabaseSession,
    authenticated_session: AuthenticatedSessionDependency,
) -> CvExtractionResponse:
    extraction = await get_owned_extraction(
        database_session,
        user_id=authenticated_session.principal.user_id,
        document_id=document_id,
        version_id=version_id,
    )
    return extraction_response(extraction)


@router.post(
    "/cv-documents/{document_id}/versions/{version_id}/extraction",
    response_model=CvExtractionResponse,
)
async def create_extraction(
    document_id: UUID,
    version_id: UUID,
    request: Request,
    database_session: DatabaseSession,
    authenticated_session: AuthenticatedSessionDependency,
    submitted_csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> CvExtractionResponse:
    settings: Settings = request.app.state.settings
    require_csrf_token(
        submitted_token=submitted_csrf_token,
        cookie_token=request.cookies.get(CSRF_COOKIE_NAME),
        authenticated_session=authenticated_session,
        settings=settings,
    )
    storage: PrivateObjectStorage = request.app.state.object_storage
    extraction = await extract_owned_version(
        database_session,
        storage,
        user_id=authenticated_session.principal.user_id,
        document_id=document_id,
        version_id=version_id,
        max_upload_bytes=settings.max_upload_bytes,
    )
    return extraction_response(extraction)
