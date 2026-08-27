from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CvExtraction(Base):
    __tablename__ = "cv_extractions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processing', 'succeeded', 'failed')",
            name="ck_cv_extraction_status",
        ),
        CheckConstraint(
            "source_type IN ('pdf', 'docx')",
            name="ck_cv_extraction_source_type",
        ),
        CheckConstraint(
            "character_count >= 0",
            name="ck_cv_extraction_character_count_nonnegative",
        ),
        UniqueConstraint("document_version_id"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    document_version_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("cv_document_versions.id", ondelete="CASCADE"),
        index=True,
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(12), nullable=False)
    character_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    parser_version: Mapped[str] = mapped_column(
        String(64), nullable=False, default="bounded-text-v2"
    )
    quality: Mapped[str] = mapped_column(String(16), nullable=False, default="unknown")
    warnings: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    failure_message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
