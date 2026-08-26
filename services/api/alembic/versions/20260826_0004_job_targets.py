"""Job target intake.

Revision ID: 20260826_0004
Revises: 20260826_0003
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260826_0004"
down_revision: str | Sequence[str] | None = "20260826_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "job_targets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("company", sa.String(length=180), nullable=True),
        sa.Column("location", sa.String(length=180), nullable=True),
        sa.Column("job_description", sa.Text(), nullable=False),
        sa.Column("job_description_character_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "job_description_character_count >= 0",
            name="ck_job_target_description_character_count_nonnegative",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_job_targets_user_id", "job_targets", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_job_targets_user_id", table_name="job_targets")
    op.drop_table("job_targets")
