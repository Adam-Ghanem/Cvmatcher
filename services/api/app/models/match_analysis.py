from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MatchAnalysis(Base):
    """Owner-scoped deterministic result for one CV version and one target role."""

    __tablename__ = "match_analyses"
    __table_args__ = (
        UniqueConstraint(
            "cv_document_version_id",
            "job_target_id",
            "scoring_version",
            name="uq_match_analysis_input_version",
        ),
        CheckConstraint(
            "overall_score >= 0 AND overall_score <= 100", name="ck_match_analysis_score_range"
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    cv_document_version_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("cv_document_versions.id", ondelete="CASCADE"),
        index=True,
    )
    job_target_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("job_targets.id", ondelete="CASCADE"),
        index=True,
    )
    scoring_version: Mapped[str] = mapped_column(String(64), nullable=False)
    overall_score: Mapped[int] = mapped_column(nullable=False)
    result_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
