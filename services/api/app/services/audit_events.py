from __future__ import annotations

from typing import Final
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.logging import request_id_context
from app.models.audit_event import AuditEvent

type AuditMetadataValue = str | int | bool | None

ALLOWED_EVENT_METADATA: Final = {
    "auth.account_created": frozenset({"authentication_method"}),
    "auth.session_issued": frozenset({"authentication_method"}),
    "auth.session_revoked": frozenset(),
    "auth.login_failed": frozenset({"reason"}),
    "auth.login_succeeded": frozenset(),
    "cv.uploaded": frozenset(),
    "cv.deleted": frozenset(),
    "target.created": frozenset(),
    "target.deleted": frozenset(),
    "cv.extraction_succeeded": frozenset({"source_type", "quality"}),
    "cv.extraction_failed": frozenset({"source_type"}),
    "analysis.created": frozenset({"scoring_version"}),
    "analysis.reused": frozenset({"scoring_version"}),
    "action_plan.generated": frozenset({"created_count"}),
    "action.status_updated": frozenset({"status"}),
}
MAX_AUDIT_METADATA_STRING_LENGTH: Final = 64


def record_audit_event(
    database_session: AsyncSession,
    *,
    event_type: str,
    user_id: UUID | None,
    metadata: dict[str, AuditMetadataValue],
) -> None:
    allowed_keys = ALLOWED_EVENT_METADATA.get(event_type)
    if allowed_keys is None:
        raise ValueError("Unsupported audit event type.")
    if set(metadata) != allowed_keys:
        raise ValueError("Unexpected audit event metadata fields.")
    for value in metadata.values():
        if isinstance(value, str) and len(value) > MAX_AUDIT_METADATA_STRING_LENGTH:
            raise ValueError("Audit metadata string is too long.")
        if not isinstance(value, (str, int, bool, type(None))):
            raise ValueError("Audit metadata must be a bounded scalar value.")
    database_session.add(
        AuditEvent(
            event_type=event_type,
            user_id=user_id,
            request_id=request_id_context.get(),
            metadata_json=metadata,
        )
    )


async def record_committed_audit_event(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    event_type: str,
    user_id: UUID | None,
    metadata: dict[str, AuditMetadataValue],
) -> None:
    """Persist an allowlisted event when the caller's primary transaction must roll back."""
    async with session_factory() as database_session:
        record_audit_event(
            database_session,
            event_type=event_type,
            user_id=user_id,
            metadata=metadata,
        )
        await database_session.commit()
