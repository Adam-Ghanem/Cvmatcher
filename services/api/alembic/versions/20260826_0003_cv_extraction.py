"""CV extraction state.

Revision ID: 20260826_0003
Revises: 20260826_0002
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260826_0003"
down_revision: str | Sequence[str] | None = "20260826_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cv_extractions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("source_type", sa.String(length=12), nullable=False),
        sa.Column("character_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("failure_message", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'succeeded', 'failed')",
            name="ck_cv_extraction_status",
        ),
        sa.CheckConstraint(
            "source_type IN ('pdf', 'docx')",
            name="ck_cv_extraction_source_type",
        ),
        sa.CheckConstraint(
            "character_count >= 0",
            name="ck_cv_extraction_character_count_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            ["cv_document_versions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_version_id"),
    )
    op.create_index(
        "ix_cv_extractions_document_version_id",
        "cv_extractions",
        ["document_version_id"],
    )
    op.create_index("ix_cv_extractions_status", "cv_extractions", ["status"])


def downgrade() -> None:
    op.drop_index("ix_cv_extractions_status", table_name="cv_extractions")
    op.drop_index("ix_cv_extractions_document_version_id", table_name="cv_extractions")
    op.drop_table("cv_extractions")
