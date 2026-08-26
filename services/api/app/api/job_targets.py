from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Header, Query, Request, status

from app.api.cv_documents import validate_authenticated_csrf
from app.api.dependencies import AuthenticatedSessionDependency, DatabaseSession
from app.schemas.job_requirements import (
    CreateJobRequirementRequest,
    JobRequirementListResponse,
    JobRequirementResponse,
    UpdateJobRequirementRequest,
)
from app.schemas.job_targets import CreateJobTargetRequest, JobTargetListResponse, JobTargetSummary
from app.services.job_requirements import JobRequirementService
from app.services.job_targets import JobTargetService

router = APIRouter(prefix="/job-targets", tags=["job targets"])


def job_target_service() -> JobTargetService:
    return JobTargetService()


@router.get("", response_model=JobTargetListResponse)
async def list_job_targets(
    database_session: DatabaseSession,
    authenticated_session: AuthenticatedSessionDependency,
) -> JobTargetListResponse:
    targets = await job_target_service().list_targets(
        database_session,
        user_id=authenticated_session.principal.user_id,
    )
    return JobTargetListResponse(data=targets)


@router.get("/{target_id}/requirements", response_model=JobRequirementListResponse)
async def list_job_requirements(
    target_id: UUID,
    database_session: DatabaseSession,
    authenticated_session: AuthenticatedSessionDependency,
    limit: int = Query(default=20, ge=1, le=50),
    cursor: UUID | None = None,
) -> JobRequirementListResponse:
    return await JobRequirementService().list_requirements(
        database_session,
        user_id=authenticated_session.principal.user_id,
        target_id=target_id,
        limit=limit,
        cursor=cursor,
    )


@router.post(
    "/{target_id}/requirements",
    response_model=JobRequirementResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_job_requirement(
    target_id: UUID,
    payload: CreateJobRequirementRequest,
    request: Request,
    database_session: DatabaseSession,
    authenticated_session: AuthenticatedSessionDependency,
    submitted_csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> JobRequirementResponse:
    validate_authenticated_csrf(
        request,
        authenticated_session=authenticated_session,
        submitted_csrf_token=submitted_csrf_token,
    )
    return await JobRequirementService().create_requirement(
        database_session,
        user_id=authenticated_session.principal.user_id,
        target_id=target_id,
        payload=payload,
    )


@router.patch("/{target_id}/requirements/{requirement_id}", response_model=JobRequirementResponse)
async def update_job_requirement(
    target_id: UUID,
    requirement_id: UUID,
    payload: UpdateJobRequirementRequest,
    request: Request,
    database_session: DatabaseSession,
    authenticated_session: AuthenticatedSessionDependency,
    submitted_csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> JobRequirementResponse:
    validate_authenticated_csrf(
        request,
        authenticated_session=authenticated_session,
        submitted_csrf_token=submitted_csrf_token,
    )
    return await JobRequirementService().update_requirement(
        database_session,
        user_id=authenticated_session.principal.user_id,
        target_id=target_id,
        requirement_id=requirement_id,
        payload=payload,
    )


@router.delete(
    "/{target_id}/requirements/{requirement_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_job_requirement(
    target_id: UUID,
    requirement_id: UUID,
    request: Request,
    database_session: DatabaseSession,
    authenticated_session: AuthenticatedSessionDependency,
    submitted_csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> None:
    validate_authenticated_csrf(
        request,
        authenticated_session=authenticated_session,
        submitted_csrf_token=submitted_csrf_token,
    )
    await JobRequirementService().delete_requirement(
        database_session,
        user_id=authenticated_session.principal.user_id,
        target_id=target_id,
        requirement_id=requirement_id,
    )


@router.delete("/{target_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job_target(
    target_id: UUID,
    request: Request,
    database_session: DatabaseSession,
    authenticated_session: AuthenticatedSessionDependency,
    submitted_csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> None:
    validate_authenticated_csrf(
        request,
        authenticated_session=authenticated_session,
        submitted_csrf_token=submitted_csrf_token,
    )
    await job_target_service().delete_target(
        database_session,
        user_id=authenticated_session.principal.user_id,
        target_id=target_id,
    )


@router.post("", response_model=JobTargetSummary, status_code=status.HTTP_201_CREATED)
async def create_job_target(
    payload: CreateJobTargetRequest,
    request: Request,
    database_session: DatabaseSession,
    authenticated_session: AuthenticatedSessionDependency,
    submitted_csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> JobTargetSummary:
    validate_authenticated_csrf(
        request,
        authenticated_session=authenticated_session,
        submitted_csrf_token=submitted_csrf_token,
    )
    return await job_target_service().create_target(
        database_session,
        user_id=authenticated_session.principal.user_id,
        payload=payload,
    )
