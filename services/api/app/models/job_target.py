from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class JobTarget(Base):
    """A user-owned target role with private, untrusted job-description text."""

    __tablename__ = "job_targets"
    __table_args__ = (
        CheckConstraint(
            "job_description_character_count >= 0",
            name="ck_job_target_description_character_count_nonnegative",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    company: Mapped[str | None] = mapped_column(String(180), nullable=True)
    location: Mapped[str | None] = mapped_column(String(180), nullable=True)
    job_description: Mapped[str] = mapped_column(Text, nullable=False)
    job_description_character_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
