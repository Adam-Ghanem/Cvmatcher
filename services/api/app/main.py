from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncEngine
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import RequestResponseEndpoint

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.errors import ApiException
from app.core.logging import configure_logging, request_id_context
from app.core.rate_limit import (
    InMemoryRateLimitBackend,
    RateLimitBackend,
    RateLimitDecision,
    RateLimitPolicy,
    RateLimitService,
)
from app.core.request_limits import RequestBodyLimitMiddleware
from app.db.session import create_database_engine, create_session_factory
from app.schemas.common import ApiErrorDetail, ApiErrorResponse
from app.services.object_storage import LocalPrivateObjectStorage

logger = logging.getLogger(__name__)
RateLimitBackendFactory = Callable[[Settings], RateLimitBackend]


def default_rate_limit_backend_factory(settings: Settings) -> RateLimitBackend:
    if settings.rate_limit_backend == "local":
        return InMemoryRateLimitBackend()
    raise RuntimeError(
        "A shared rate-limit backend factory must be configured for this deployment."
    )


def rate_limit_policy_for_request(request: Request, settings: Settings) -> RateLimitPolicy:
    if request.url.path.startswith(f"{settings.api_v1_prefix}/auth/"):
        return RateLimitPolicy(
            name="auth",
            limit=settings.auth_rate_limit_requests_per_minute,
            window_seconds=settings.rate_limit_window_seconds,
        )
    if request.method == "POST" and (
        request.url.path == f"{settings.api_v1_prefix}/match-analyses"
        or request.url.path.endswith("/extraction")
        or request.url.path.endswith("/actions")
    ):
        return RateLimitPolicy(
            name="expensive",
            limit=settings.expensive_rate_limit_requests_per_minute,
            window_seconds=settings.rate_limit_window_seconds,
        )
    return RateLimitPolicy(
        name="general",
        limit=settings.rate_limit_requests_per_minute,
        window_seconds=settings.rate_limit_window_seconds,
    )


def add_rate_limit_headers(response: Response, decision: RateLimitDecision) -> None:
    response.headers["RateLimit-Limit"] = str(decision.limit)
    response.headers["RateLimit-Remaining"] = str(decision.remaining)
    response.headers["RateLimit-Reset"] = str(decision.reset_after_seconds)
    if decision.retry_after_seconds is not None:
        response.headers["Retry-After"] = str(decision.retry_after_seconds)


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
    application.state.session_factory = create_session_factory(database_engine)
    rate_limit_backend_factory: RateLimitBackendFactory = (
        application.state.rate_limit_backend_factory
    )
    application.state.rate_limit_service = RateLimitService(
        rate_limit_backend_factory(settings),
        fail_closed_on_backend_error=settings.rate_limit_fail_closed_on_backend_error,
    )
    application.state.object_storage = LocalPrivateObjectStorage(
        settings.resolved_private_storage_root
    )
    try:
        yield
    finally:
        await database_engine.dispose()


def create_app(
    settings: Settings | None = None,
    *,
    rate_limit_backend_factory: RateLimitBackendFactory | None = None,
) -> FastAPI:
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
    application.state.rate_limit_backend_factory = (
        rate_limit_backend_factory or default_rate_limit_backend_factory
    )
    application.add_middleware(
        RequestBodyLimitMiddleware,
        max_request_body_bytes=resolved_settings.max_request_body_bytes,
        max_multipart_request_bytes=resolved_settings.max_multipart_request_bytes,
    )

    @application.middleware("http")
    async def security_and_request_context(
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request_id = request_id_from_header(request.headers.get("X-Request-ID"))
        request.state.request_id = request_id
        context_token = request_id_context.set(request_id)
        request_started_at = perf_counter()
        response: Response
        try:
            rate_limit_decision: RateLimitDecision | None = None
            if request.url.path not in {"/api/v1/health", "/api/v1/ready"}:
                client_host = request.client.host if request.client else "unknown"
                rate_limit_service: RateLimitService = request.app.state.rate_limit_service
                rate_limit_decision = await rate_limit_service.check(
                    policy=rate_limit_policy_for_request(request, resolved_settings),
                    key=client_host,
                )
                if not rate_limit_decision.allowed:
                    if rate_limit_decision.backend_available:
                        response = error_response(
                            request,
                            code="RATE_LIMITED",
                            message="Too many requests. Please try again shortly.",
                            status_code=429,
                        )
                    else:
                        response = error_response(
                            request,
                            code="RATE_LIMIT_UNAVAILABLE",
                            message=(
                                "This service is temporarily unavailable. Please try again shortly."
                            ),
                            status_code=503,
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
            route = request.scope.get("route")
            route_template = getattr(route, "path", "unmatched")
            logger.info(
                "request completed",
                extra={
                    "event": {
                        "method": request.method,
                        "route": route_template,
                        "status_code": response.status_code,
                        "duration_ms": max(0, round((perf_counter() - request_started_at) * 1000)),
                    }
                },
            )
            request_id_context.reset(context_token)

        response.headers["X-Request-ID"] = request_id
        if rate_limit_decision is not None:
            add_rate_limit_headers(response, rate_limit_decision)
        add_security_headers(response, resolved_settings)
        return response

    application.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origin_strings,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Accept", "Content-Type", "X-Request-ID", "X-CSRF-Token"],
        expose_headers=["X-Request-ID"],
        max_age=600,
    )

    @application.exception_handler(ApiException)
    async def handle_api_exception(request: Request, exc: ApiException) -> JSONResponse:
        return error_response(request, exc.code, exc.message, exc.status_code)

    @application.exception_handler(StarletteHTTPException)
    async def handle_framework_http_error(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        code, message = {
            404: ("RESOURCE_NOT_FOUND", "We could not find that resource."),
            405: ("METHOD_NOT_ALLOWED", "This request method is not supported for that resource."),
        }.get(
            exc.status_code,
            ("REQUEST_ERROR", "We could not process this request."),
        )
        response = error_response(request, code, message, exc.status_code)
        if exc.headers:
            response.headers.update(exc.headers)
        return response

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
