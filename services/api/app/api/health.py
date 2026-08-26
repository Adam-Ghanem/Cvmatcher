from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.db.session import is_database_ready
from app.schemas.common import ApiErrorDetail, ApiErrorResponse, HealthResponse, ReadinessResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={503: {"model": ApiErrorResponse}},
)
async def readiness(request: Request) -> ReadinessResponse | JSONResponse:
    if await is_database_ready(request.app.state.database_engine):
        return ReadinessResponse(status="ready", database="ready")

    return JSONResponse(
        status_code=503,
        content=ApiErrorResponse(
            error=ApiErrorDetail(
                code="DEPENDENCY_UNAVAILABLE",
                message="The service is not ready. Please try again shortly.",
                requestId=request.state.request_id,
            )
        ).model_dump(by_alias=True),
    )
