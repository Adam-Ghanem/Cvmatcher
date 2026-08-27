from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AnalysisAction(Base):
    """A deterministic action derived from one persisted analysis requirement gap."""

    __tablename__ = "analysis_actions"
    __table_args__ = (
        CheckConstraint(
            "category IN ('must-have', 'should-have', 'nice-to-have')",
            name="ck_analysis_action_category",
        ),
        CheckConstraint("priority BETWEEN 1 AND 400", name="ck_analysis_action_priority_range"),
        CheckConstraint("position >= 1", name="ck_analysis_action_position_positive"),
        CheckConstraint(
            "status IN ('todo', 'in_progress', 'completed')",
            name="ck_analysis_action_status",
        ),
        UniqueConstraint(
            "analysis_id",
            "requirement_id",
            name="uq_analysis_action_analysis_requirement",
        ),
        Index("ix_analysis_actions_analysis_position_id", "analysis_id", "position", "id"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    analysis_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("match_analyses.id", ondelete="CASCADE"),
        index=True,
    )
    requirement_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("job_requirements.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(String(600), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(16), nullable=False)
    evidence_state: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="todo")
    position: Mapped[int] = mapped_column(Integer, nullable=False)
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
