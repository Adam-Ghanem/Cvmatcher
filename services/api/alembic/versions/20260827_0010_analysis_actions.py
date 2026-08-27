"""Add deterministic analysis actions.

Revision ID: 20260827_0010
Revises: 20260826_0009
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260827_0010"
down_revision: str | Sequence[str] | None = "20260826_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analysis_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requirement_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("description", sa.String(length=600), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=16), nullable=False),
        sa.Column("evidence_state", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
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
            "category IN ('must-have', 'should-have', 'nice-to-have')",
            name="ck_analysis_action_category",
        ),
        sa.CheckConstraint(
            "priority BETWEEN 1 AND 400",
            name="ck_analysis_action_priority_range",
        ),
        sa.CheckConstraint("position >= 1", name="ck_analysis_action_position_positive"),
        sa.CheckConstraint(
            "status IN ('todo', 'in_progress', 'completed')",
            name="ck_analysis_action_status",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["analysis_id"], ["match_analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requirement_id"], ["job_requirements.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "analysis_id",
            "requirement_id",
            name="uq_analysis_action_analysis_requirement",
        ),
    )
    op.create_index("ix_analysis_actions_user_id", "analysis_actions", ["user_id"])
    op.create_index("ix_analysis_actions_analysis_id", "analysis_actions", ["analysis_id"])
    op.create_index("ix_analysis_actions_requirement_id", "analysis_actions", ["requirement_id"])
    op.create_index(
        "ix_analysis_actions_analysis_position_id",
        "analysis_actions",
        ["analysis_id", "position", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_analysis_actions_analysis_position_id", table_name="analysis_actions")
    op.drop_index("ix_analysis_actions_requirement_id", table_name="analysis_actions")
    op.drop_index("ix_analysis_actions_analysis_id", table_name="analysis_actions")
    op.drop_index("ix_analysis_actions_user_id", table_name="analysis_actions")
    op.drop_table("analysis_actions")
