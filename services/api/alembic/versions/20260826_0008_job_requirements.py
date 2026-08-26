"""Add structured job requirements.

Revision ID: 20260826_0008
Revises: 20260826_0007
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260826_0008"
down_revision: str | Sequence[str] | None = "20260826_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "job_requirements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requirement_text", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=16), nullable=False),
        sa.Column("normalized_skill", sa.String(length=180), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("source_reference", sa.String(length=500), nullable=True),
        sa.Column("normalization_version", sa.String(length=64), nullable=False),
        sa.Column("review_state", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "char_length(requirement_text) BETWEEN 2 AND 1000",
            name="ck_job_requirement_text_length",
        ),
        sa.CheckConstraint(
            "category IN ('must-have', 'should-have', 'nice-to-have')",
            name="ck_job_requirement_category",
        ),
        sa.CheckConstraint(
            "priority BETWEEN 1 AND 100",
            name="ck_job_requirement_priority_range",
        ),
        sa.CheckConstraint(
            "review_state IN ('unreviewed', 'reviewed', 'user-confirmed')",
            name="ck_job_requirement_review_state",
        ),
        sa.ForeignKeyConstraint(["job_target_id"], ["job_targets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_job_requirements_user_id", "job_requirements", ["user_id"])
    op.create_index("ix_job_requirements_job_target_id", "job_requirements", ["job_target_id"])
    op.create_index(
        "ix_job_requirements_target_priority_created_id",
        "job_requirements",
        ["job_target_id", "priority", "created_at", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_job_requirements_target_priority_created_id", table_name="job_requirements")
    op.drop_index("ix_job_requirements_job_target_id", table_name="job_requirements")
    op.drop_index("ix_job_requirements_user_id", table_name="job_requirements")
    op.drop_table("job_requirements")
