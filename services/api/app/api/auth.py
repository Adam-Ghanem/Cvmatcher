from __future__ import annotations

import secrets

from fastapi import APIRouter, Header, Request, Response, status

from app.api.dependencies import AuthenticatedSessionDependency, DatabaseSession
from app.core.config import Settings
from app.schemas.auth import AuthenticatedUserResponse, CredentialsRequest, CsrfTokenResponse
from app.services.authentication import (
    CSRF_COOKIE_NAME,
    SESSION_COOKIE_NAME,
    create_user_with_password,
    issue_session,
    public_user,
    require_csrf_token,
    resolve_authenticated_session,
    revoke_session,
    secret_digest,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


def set_session_cookies(
    response: Response,
    *,
    session_token: str,
    csrf_token: str,
    settings: Settings,
) -> None:
    max_age = settings.session_ttl_hours * 60 * 60
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        max_age=max_age,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        max_age=max_age,
        httponly=False,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
    )


def validate_unauthenticated_csrf(
    request: Request,
    submitted_csrf_token: str | None,
    settings: Settings,
) -> None:
    require_csrf_token(
        submitted_token=submitted_csrf_token,
        cookie_token=request.cookies.get(CSRF_COOKIE_NAME),
        authenticated_session=None,
        settings=settings,
    )


@router.get("/csrf", response_model=CsrfTokenResponse)
async def csrf_bootstrap(
    request: Request,
    response: Response,
    database_session: DatabaseSession,
) -> CsrfTokenResponse:
    settings: Settings = request.app.state.settings
    csrf_token = secrets.token_urlsafe(32)
    raw_session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if raw_session_token:
        authenticated_session = await resolve_authenticated_session(
            database_session,
            raw_session_token=raw_session_token,
            settings=settings,
        )
        authenticated_session.session.csrf_token_digest = secret_digest(csrf_token, settings)
        await database_session.flush()
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        max_age=settings.session_ttl_hours * 60 * 60,
        httponly=False,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
    )
    return CsrfTokenResponse(csrf_token=csrf_token)


@router.post(
    "/register", response_model=AuthenticatedUserResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    credentials: CredentialsRequest,
    request: Request,
    response: Response,
    database_session: DatabaseSession,
    submitted_csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> AuthenticatedUserResponse:
    settings: Settings = request.app.state.settings
    validate_unauthenticated_csrf(request, submitted_csrf_token, settings)
    user = await create_user_with_password(
        database_session,
        email=credentials.email,
        password=credentials.password,
    )
    issued_session = await issue_session(
        database_session,
        user=user,
        settings=settings,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    set_session_cookies(
        response,
        session_token=issued_session.session_token,
        csrf_token=issued_session.csrf_token,
        settings=settings,
    )
    return AuthenticatedUserResponse(user=public_user(user))


@router.post("/login", response_model=AuthenticatedUserResponse)
async def login(
    credentials: CredentialsRequest,
    request: Request,
    response: Response,
    database_session: DatabaseSession,
    submitted_csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> AuthenticatedUserResponse:
    settings: Settings = request.app.state.settings
    validate_unauthenticated_csrf(request, submitted_csrf_token, settings)
    from app.services.authentication import authenticate_password

    user = await authenticate_password(
        database_session,
        email=credentials.email,
        password=credentials.password,
    )
    issued_session = await issue_session(
        database_session,
        user=user,
        settings=settings,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    set_session_cookies(
        response,
        session_token=issued_session.session_token,
        csrf_token=issued_session.csrf_token,
        settings=settings,
    )
    return AuthenticatedUserResponse(user=public_user(user))


@router.get("/me", response_model=AuthenticatedUserResponse)
async def me(authenticated_session: AuthenticatedSessionDependency) -> AuthenticatedUserResponse:
    return AuthenticatedUserResponse(user=public_user(authenticated_session.user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    database_session: DatabaseSession,
    authenticated_session: AuthenticatedSessionDependency,
    submitted_csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> Response:
    settings: Settings = request.app.state.settings
    require_csrf_token(
        submitted_token=submitted_csrf_token,
        cookie_token=request.cookies.get(CSRF_COOKIE_NAME),
        authenticated_session=authenticated_session,
        settings=settings,
    )
    await revoke_session(database_session, authenticated_session.session)
    response.status_code = status.HTTP_204_NO_CONTENT
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    response.delete_cookie(key=CSRF_COOKIE_NAME, path="/")
    return response
