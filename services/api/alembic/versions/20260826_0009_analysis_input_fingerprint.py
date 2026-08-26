"""Add version-aware analysis input fingerprints.

Revision ID: 20260826_0009
Revises: 20260826_0008
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260826_0009"
down_revision: str | Sequence[str] | None = "20260826_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "match_analyses",
        sa.Column("input_fingerprint", sa.String(length=64), nullable=True),
    )
    op.execute(
        "UPDATE match_analyses "
        "SET input_fingerprint = md5('legacy-v2:' || id::text) || md5(id::text)"
    )
    op.alter_column("match_analyses", "input_fingerprint", nullable=False)
    op.drop_constraint("uq_match_analysis_input_version", "match_analyses", type_="unique")
    op.create_unique_constraint(
        "uq_match_analysis_input_fingerprint",
        "match_analyses",
        ["cv_document_version_id", "job_target_id", "scoring_version", "input_fingerprint"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_match_analysis_input_fingerprint", "match_analyses", type_="unique")
    op.drop_column("match_analyses", "input_fingerprint")
    op.create_unique_constraint(
        "uq_match_analysis_input_version",
        "match_analyses",
        ["cv_document_version_id", "job_target_id", "scoring_version"],
    )
