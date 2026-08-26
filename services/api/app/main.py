from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncEngine
from starlette.middleware.base import RequestResponseEndpoint

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.errors import ApiException
from app.core.logging import configure_logging, request_id_context
from app.core.rate_limit import InMemoryRateLimiter
from app.db.session import create_database_engine
from app.schemas.common import ApiErrorDetail, ApiErrorResponse

logger = logging.getLogger(__name__)


def request_id_from_header(value: str | None) -> str:
    if value is None:
        return str(uuid4())
    try:
        return str(UUID(value))
    except ValueError:
        return str(uuid4())


def error_response(request: Request, code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ApiErrorResponse(
            error=ApiErrorDetail(code=code, message=message, requestId=request.state.request_id)
        ).model_dump(by_alias=True),
    )


def add_security_headers(response: Response, settings: Settings) -> None:
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; base-uri 'self'; frame-ancestors 'none'"
    )
    if settings.app_env == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    settings: Settings = application.state.settings
    database_engine: AsyncEngine = create_database_engine(settings)
    application.state.database_engine = database_engine
    application.state.rate_limiter = InMemoryRateLimiter(
        max_requests=settings.rate_limit_requests_per_minute
    )
    try:
        yield
    finally:
        await database_engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings.log_level)

    application = FastAPI(
        title=resolved_settings.app_name,
        version="0.1.0",
        openapi_url=f"{resolved_settings.api_v1_prefix}/openapi.json",
        docs_url=None if resolved_settings.app_env == "production" else "/docs",
        redoc_url=None,
        lifespan=lifespan,
    )
    application.state.settings = resolved_settings
    application.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origin_strings,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Accept", "Content-Type", "X-Request-ID", "X-CSRF-Token"],
        expose_headers=["X-Request-ID"],
        max_age=600,
    )

    @application.middleware("http")
    async def security_and_request_context(
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request_id = request_id_from_header(request.headers.get("X-Request-ID"))
        request.state.request_id = request_id
        context_token = request_id_context.set(request_id)
        response: Response
        try:
            if request.url.path not in {"/api/v1/health", "/api/v1/ready"}:
                client_host = request.client.host if request.client else "unknown"
                if not await request.app.state.rate_limiter.allow(client_host):
                    response = error_response(
                        request,
                        code="RATE_LIMITED",
                        message="Too many requests. Please try again shortly.",
                        status_code=429,
                    )
                else:
                    response = await call_next(request)
            else:
                response = await call_next(request)
        except ApiException as exc:
            response = error_response(request, exc.code, exc.message, exc.status_code)
        except Exception as exc:
            logger.exception(
                "unexpected middleware failure",
                extra={"event": {"exception": type(exc).__name__}},
            )
            response = error_response(
                request,
                code="INTERNAL_ERROR",
                message="We could not complete this request. Please try again.",
                status_code=500,
            )
        finally:
            request_id_context.reset(context_token)

        response.headers["X-Request-ID"] = request_id
        add_security_headers(response, resolved_settings)
        return response

    @application.exception_handler(ApiException)
    async def handle_api_exception(request: Request, exc: ApiException) -> JSONResponse:
        return error_response(request, exc.code, exc.message, exc.status_code)

    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.info(
            "request validation failed",
            extra={"event": {"errors": len(exc.errors())}},
        )
        return error_response(
            request,
            code="VALIDATION_ERROR",
            message=(
                "The request could not be understood. Check the submitted values and try again."
            ),
            status_code=422,
        )

    @application.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "unexpected request failure",
            extra={"event": {"exception": type(exc).__name__}},
        )
        return error_response(
            request,
            code="INTERNAL_ERROR",
            message="We could not complete this request. Please try again.",
            status_code=500,
        )

    application.include_router(api_router, prefix=resolved_settings.api_v1_prefix)
    return application


app = create_app()
