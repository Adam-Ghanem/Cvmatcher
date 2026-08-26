from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PrivateObjectKey:
    """Opaque storage identifier. It must never contain a client-supplied path."""

    value: str


class PrivateObjectStorage(Protocol):
    """Server-only storage contract for future sensitive CV documents."""

    async def put(
        self,
        *,
        owner_id: UUID,
        object_key: PrivateObjectKey,
        content_type: str,
        content: AsyncIterator[bytes],
    ) -> None: ...

    async def delete(self, *, owner_id: UUID, object_key: PrivateObjectKey) -> None: ...
