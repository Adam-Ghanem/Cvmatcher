"""Add safe extraction metadata.

Revision ID: 20260826_0006
Revises: 20260826_0005
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260826_0006"
down_revision: str | Sequence[str] | None = "20260826_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "cv_extractions",
        sa.Column(
            "parser_version",
            sa.String(length=64),
            nullable=False,
            server_default="bounded-text-v2",
        ),
    )
    op.add_column(
        "cv_extractions",
        sa.Column("quality", sa.String(length=16), nullable=False, server_default="unknown"),
    )
    op.add_column(
        "cv_extractions",
        sa.Column(
            "warnings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("cv_extractions", "warnings")
    op.drop_column("cv_extractions", "quality")
    op.drop_column("cv_extractions", "parser_version")
