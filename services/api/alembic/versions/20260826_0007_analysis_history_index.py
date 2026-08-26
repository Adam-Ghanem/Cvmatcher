"""Add analysis history pagination index.

Revision ID: 20260826_0007
Revises: 20260826_0006
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260826_0007"
down_revision: str | Sequence[str] | None = "20260826_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_match_analyses_user_created_id",
        "match_analyses",
        ["user_id", "created_at", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_match_analyses_user_created_id", table_name="match_analyses")
