from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.services.authentication import (
    SESSION_COOKIE_NAME,
    AuthenticatedSession,
    resolve_authenticated_session,
)


async def get_database_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    session_factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with session_factory() as database_session:
        try:
            yield database_session
            await database_session.commit()
        except Exception:
            await database_session.rollback()
            raise


DatabaseSession = Annotated[AsyncSession, Depends(get_database_session)]


async def require_authenticated_session(
    request: Request,
    database_session: DatabaseSession,
) -> AuthenticatedSession:
    settings: Settings = request.app.state.settings
    return await resolve_authenticated_session(
        database_session,
        raw_session_token=request.cookies.get(SESSION_COOKIE_NAME),
        settings=settings,
    )


AuthenticatedSessionDependency = Annotated[
    AuthenticatedSession, Depends(require_authenticated_session)
]
