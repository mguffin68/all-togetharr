"""Add overview, poster_path to titles and name to episodes.

Revision ID: 0007_title_metadata
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_title_metadata"
down_revision: str | None = "0006_catalog"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "titles",
        sa.Column("overview", sa.Text(), nullable=True),
    )
    op.add_column(
        "titles",
        sa.Column("poster_path", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "episodes",
        sa.Column("name", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("episodes", "name")
    op.drop_column("titles", "poster_path")
    op.drop_column("titles", "overview")
