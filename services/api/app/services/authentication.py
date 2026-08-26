from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import ApiException
from app.models.password_credential import PasswordCredential
from app.models.user import User
from app.models.user_session import UserSession
from app.schemas.auth import PublicUser
from app.services.authorization import CurrentPrincipal

PASSWORD_HASHER = PasswordHasher()
SESSION_COOKIE_NAME = "cvmatcher_session"
CSRF_COOKIE_NAME = "cvmatcher_csrf"


@dataclass(frozen=True, slots=True)
class IssuedSession:
    session_token: str
    csrf_token: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class AuthenticatedSession:
    principal: CurrentPrincipal
    user: User
    session: UserSession


def now_utc() -> datetime:
    return datetime.now(UTC)


def secret_digest(value: str, settings: Settings) -> str:
    return hmac.new(
        settings.session_hmac_secret.get_secret_value().encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def request_metadata_hash(value: str | None, settings: Settings) -> str | None:
    if not value:
        return None
    return secret_digest(value, settings)


def hash_password(password: str) -> str:
    return PASSWORD_HASHER.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return PASSWORD_HASHER.verify(password_hash, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def public_user(user: User) -> PublicUser:
    return PublicUser(id=user.id, email=user.email, created_at=user.created_at)


async def create_user_with_password(
    database_session: AsyncSession,
    *,
    email: str,
    password: str,
) -> User:
    existing_user = await database_session.scalar(select(User.id).where(User.email == email))
    if existing_user is not None:
        raise ApiException(
            code="ACCOUNT_UNAVAILABLE",
            message="We could not create this account. Try signing in instead.",
            status_code=409,
        )

    user_id = uuid4()
    user = User(id=user_id, auth_subject=f"local:{user_id}", email=email)
    database_session.add(user)
    await database_session.flush()
    credential = PasswordCredential(user_id=user.id, password_hash=hash_password(password))
    database_session.add(credential)
    await database_session.flush()
    await database_session.refresh(user)
    return user


async def authenticate_password(
    database_session: AsyncSession,
    *,
    email: str,
    password: str,
) -> User:
    result = await database_session.execute(
        select(User, PasswordCredential)
        .join(PasswordCredential, PasswordCredential.user_id == User.id)
        .where(User.email == email)
    )
    row = result.tuples().one_or_none()
    if row is None:
        raise ApiException(
            code="INVALID_CREDENTIALS",
            message="Email or password is incorrect.",
            status_code=401,
        )
    user, credential = row
    if not verify_password(password, credential.password_hash):
        raise ApiException(
            code="INVALID_CREDENTIALS",
            message="Email or password is incorrect.",
            status_code=401,
        )
    return user


async def issue_session(
    database_session: AsyncSession,
    *,
    user: User,
    settings: Settings,
    user_agent: str | None,
    ip_address: str | None,
) -> IssuedSession:
    issued_at = now_utc()
    expires_at = issued_at + timedelta(hours=settings.session_ttl_hours)
    raw_session_token = secrets.token_urlsafe(48)
    raw_csrf_token = secrets.token_urlsafe(32)
    database_session.add(
        UserSession(
            user_id=user.id,
            token_digest=secret_digest(raw_session_token, settings),
            csrf_token_digest=secret_digest(raw_csrf_token, settings),
            expires_at=expires_at,
            user_agent_hash=request_metadata_hash(user_agent, settings),
            ip_address_hash=request_metadata_hash(ip_address, settings),
        )
    )
    await database_session.flush()
    return IssuedSession(
        session_token=raw_session_token,
        csrf_token=raw_csrf_token,
        expires_at=expires_at,
    )


async def resolve_authenticated_session(
    database_session: AsyncSession,
    *,
    raw_session_token: str | None,
    settings: Settings,
) -> AuthenticatedSession:
    if not raw_session_token:
        raise ApiException(
            code="AUTHENTICATION_REQUIRED",
            message="Sign in to continue.",
            status_code=401,
        )

    result = await database_session.execute(
        select(UserSession, User)
        .join(User, User.id == UserSession.user_id)
        .where(
            UserSession.token_digest == secret_digest(raw_session_token, settings),
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > now_utc(),
        )
    )
    row = result.one_or_none()
    if row is None:
        raise ApiException(
            code="AUTHENTICATION_REQUIRED",
            message="Sign in to continue.",
            status_code=401,
        )

    user_session = row.UserSession
    user_session.last_seen_at = now_utc()
    return AuthenticatedSession(
        principal=CurrentPrincipal(user_id=row.User.id, auth_subject=row.User.auth_subject),
        user=row.User,
        session=user_session,
    )


def require_csrf_token(
    *,
    submitted_token: str | None,
    cookie_token: str | None,
    authenticated_session: AuthenticatedSession | None,
    settings: Settings,
) -> None:
    if (
        not submitted_token
        or not cookie_token
        or not hmac.compare_digest(submitted_token, cookie_token)
    ):
        raise ApiException(
            code="CSRF_VALIDATION_FAILED",
            message="We could not verify this request. Refresh the page and try again.",
            status_code=403,
        )

    if authenticated_session is not None and not hmac.compare_digest(
        secret_digest(submitted_token, settings),
        authenticated_session.session.csrf_token_digest,
    ):
        raise ApiException(
            code="CSRF_VALIDATION_FAILED",
            message="We could not verify this request. Refresh the page and try again.",
            status_code=403,
        )


async def revoke_session(database_session: AsyncSession, session: UserSession) -> None:
    session.revoked_at = now_utc()
    await database_session.flush()
