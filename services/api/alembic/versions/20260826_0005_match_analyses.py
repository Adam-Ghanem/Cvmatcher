"""Deterministic match analyses.

Revision ID: 20260826_0005
Revises: 20260826_0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260826_0005"
down_revision: str | Sequence[str] | None = "20260826_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "match_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cv_document_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scoring_version", sa.String(length=64), nullable=False),
        sa.Column("overall_score", sa.Integer(), nullable=False),
        sa.Column("result_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "overall_score >= 0 AND overall_score <= 100", name="ck_match_analysis_score_range"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["cv_document_version_id"], ["cv_document_versions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["job_target_id"], ["job_targets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "cv_document_version_id",
            "job_target_id",
            "scoring_version",
            name="uq_match_analysis_input_version",
        ),
    )
    op.create_index("ix_match_analyses_user_id", "match_analyses", ["user_id"])
    op.create_index(
        "ix_match_analyses_cv_document_version_id", "match_analyses", ["cv_document_version_id"]
    )
    op.create_index("ix_match_analyses_job_target_id", "match_analyses", ["job_target_id"])


def downgrade() -> None:
    op.drop_index("ix_match_analyses_job_target_id", table_name="match_analyses")
    op.drop_index("ix_match_analyses_cv_document_version_id", table_name="match_analyses")
    op.drop_index("ix_match_analyses_user_id", table_name="match_analyses")
    op.drop_table("match_analyses")
