from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Header, Query, Request, status

from app.api.cv_documents import validate_authenticated_csrf
from app.api.dependencies import AuthenticatedSessionDependency, DatabaseSession
from app.schemas.analysis_actions import (
    AnalysisActionListResponse,
    AnalysisActionResponse,
    GenerateAnalysisActionsRequest,
    UpdateAnalysisActionRequest,
)
from app.schemas.match_analyses import (
    CreateMatchAnalysisRequest,
    MatchAnalysisHistoryResponse,
    MatchAnalysisResponse,
)
from app.services.analysis_actions import AnalysisActionService
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


@router.get("", response_model=MatchAnalysisHistoryResponse)
async def list_match_analysis_history(
    database_session: DatabaseSession,
    authenticated_session: AuthenticatedSessionDependency,
    limit: int = Query(default=20, ge=1, le=50),
    cursor: UUID | None = None,
) -> MatchAnalysisHistoryResponse:
    return await MatchAnalysisService().list_history(
        database_session,
        user_id=authenticated_session.principal.user_id,
        limit=limit,
        cursor=cursor,
    )


@router.get("/{analysis_id}/actions", response_model=AnalysisActionListResponse)
async def list_analysis_actions(
    analysis_id: UUID,
    database_session: DatabaseSession,
    authenticated_session: AuthenticatedSessionDependency,
    limit: int = Query(default=20, ge=1, le=50),
    cursor: UUID | None = None,
) -> AnalysisActionListResponse:
    return await AnalysisActionService().list_for_analysis(
        database_session,
        user_id=authenticated_session.principal.user_id,
        analysis_id=analysis_id,
        limit=limit,
        cursor=cursor,
    )


@router.post(
    "/{analysis_id}/actions",
    response_model=AnalysisActionListResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_analysis_actions(
    analysis_id: UUID,
    _payload: GenerateAnalysisActionsRequest,
    request: Request,
    database_session: DatabaseSession,
    authenticated_session: AuthenticatedSessionDependency,
    submitted_csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> AnalysisActionListResponse:
    validate_authenticated_csrf(
        request,
        authenticated_session=authenticated_session,
        submitted_csrf_token=submitted_csrf_token,
    )
    return await AnalysisActionService().generate_for_analysis(
        database_session,
        user_id=authenticated_session.principal.user_id,
        analysis_id=analysis_id,
    )


@router.patch("/{analysis_id}/actions/{action_id}", response_model=AnalysisActionResponse)
async def update_analysis_action_status(
    analysis_id: UUID,
    action_id: UUID,
    payload: UpdateAnalysisActionRequest,
    request: Request,
    database_session: DatabaseSession,
    authenticated_session: AuthenticatedSessionDependency,
    submitted_csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> AnalysisActionResponse:
    validate_authenticated_csrf(
        request,
        authenticated_session=authenticated_session,
        submitted_csrf_token=submitted_csrf_token,
    )
    return await AnalysisActionService().update_status(
        database_session,
        user_id=authenticated_session.principal.user_id,
        analysis_id=analysis_id,
        action_id=action_id,
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
