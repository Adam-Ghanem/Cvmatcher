from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Header, Request, status

from app.api.cv_documents import validate_authenticated_csrf
from app.api.dependencies import AuthenticatedSessionDependency, DatabaseSession
from app.schemas.match_analyses import CreateMatchAnalysisRequest, MatchAnalysisResponse
from app.services.match_analyses import MatchAnalysisService

router = APIRouter(prefix="/match-analyses", tags=["match analyses"])


@router.post("", response_model=MatchAnalysisResponse, status_code=status.HTTP_201_CREATED)
async def create_match_analysis(
    payload: CreateMatchAnalysisRequest,
    request: Request,
    database_session: DatabaseSession,
    authenticated_session: AuthenticatedSessionDependency,
    submitted_csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> MatchAnalysisResponse:
    validate_authenticated_csrf(
        request,
        authenticated_session=authenticated_session,
        submitted_csrf_token=submitted_csrf_token,
    )
    return await MatchAnalysisService().create_or_get(
        database_session,
        user_id=authenticated_session.principal.user_id,
        payload=payload,
    )


@router.get("/{analysis_id}", response_model=MatchAnalysisResponse)
async def get_match_analysis(
    analysis_id: UUID,
    database_session: DatabaseSession,
    authenticated_session: AuthenticatedSessionDependency,
) -> MatchAnalysisResponse:
    return await MatchAnalysisService().get_owned(
        database_session,
        user_id=authenticated_session.principal.user_id,
        analysis_id=analysis_id,
    )
