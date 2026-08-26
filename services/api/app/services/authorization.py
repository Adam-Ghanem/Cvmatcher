from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.core.errors import ApiException


@dataclass(frozen=True, slots=True)
class CurrentPrincipal:
    """Authenticated identity resolved by the server, never supplied as a body field."""

    user_id: UUID
    auth_subject: str


def require_owner(*, owner_id: UUID, principal: CurrentPrincipal) -> None:
    if owner_id != principal.user_id:
        raise ApiException(
            code="FORBIDDEN",
            message="You are not allowed to access this resource.",
            status_code=403,
        )
