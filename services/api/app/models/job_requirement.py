from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class JobRequirement(Base):
    """A reviewed, user-owned structured requirement for one private target role."""

    __tablename__ = "job_requirements"
    __table_args__ = (
        CheckConstraint(
            "char_length(requirement_text) BETWEEN 2 AND 1000",
            name="ck_job_requirement_text_length",
        ),
        CheckConstraint(
            "category IN ('must-have', 'should-have', 'nice-to-have')",
            name="ck_job_requirement_category",
        ),
        CheckConstraint(
            "priority BETWEEN 1 AND 100",
            name="ck_job_requirement_priority_range",
        ),
        CheckConstraint(
            "review_state IN ('unreviewed', 'reviewed', 'user-confirmed')",
            name="ck_job_requirement_review_state",
        ),
        Index(
            "ix_job_requirements_target_priority_created_id",
            "job_target_id",
            "priority",
            "created_at",
            "id",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    job_target_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("job_targets.id", ondelete="CASCADE"),
        index=True,
    )
    requirement_text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(16), nullable=False)
    normalized_skill: Mapped[str | None] = mapped_column(String(180), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    normalization_version: Mapped[str] = mapped_column(String(64), nullable=False)
    review_state: Mapped[str] = mapped_column(String(32), nullable=False)
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
