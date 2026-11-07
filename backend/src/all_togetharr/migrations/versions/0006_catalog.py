"""Add the catalog tables.

Revision ID: 0006_catalog
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_catalog"
down_revision: str | None = "0005_settings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "titles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "type",
            sa.Enum(
                "movie",
                "series",
                name="title_type",
                native_enum=False,
                create_constraint=True,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("tmdb_id", sa.Integer(), nullable=False),
        sa.Column("tvdb_id", sa.Integer(), nullable=True),
        sa.Column("imdb_id", sa.String(length=20), nullable=True),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "requested",
                "approved",
                "searching",
                "downloading",
                "importing",
                "available",
                name="title_status",
                native_enum=False,
                create_constraint=True,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("monitored", sa.Boolean(), nullable=False),
        sa.Column("quality_profile_id", sa.Integer(), nullable=True),
        sa.Column("root_folder_id", sa.Integer(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tmdb_id", "type", name="uq_titles_tmdb_id"),
    )

    op.create_table(
        "seasons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title_id", sa.Integer(), nullable=False),
        sa.Column("season_number", sa.Integer(), nullable=False),
        sa.Column("monitored", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("title_id", "season_number", name="uq_seasons_title_id"),
        sa.ForeignKeyConstraint(
            ["title_id"],
            ["titles.id"],
            ondelete="CASCADE",
            name="fk_seasons_title_id_titles",
        ),
    )

    op.create_table(
        "media_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title_id", sa.Integer(), nullable=False),
        sa.Column("path", sa.String(length=1024), nullable=False),
        sa.Column("size", sa.BigInteger(), nullable=False),
        sa.Column("quality", sa.String(length=100), nullable=True),
        sa.Column("custom_format_score", sa.Integer(), nullable=False),
        sa.Column("mediainfo", sa.JSON(), nullable=True),
        sa.Column("jellyfin_item_id", sa.String(length=64), nullable=True),
        sa.Column("link_key", sa.String(length=64), nullable=True),
        sa.UniqueConstraint("path", name="uq_media_files_path"),
        sa.ForeignKeyConstraint(
            ["title_id"],
            ["titles.id"],
            ondelete="CASCADE",
            name="fk_media_files_title_id_titles",
        ),
        sa.Index("ix_media_files_title_id", "title_id"),
        sa.Index("ix_media_files_link_key", "link_key"),
    )

    op.create_table(
        "episodes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title_id", sa.Integer(), nullable=False),
        sa.Column("season_number", sa.Integer(), nullable=False),
        sa.Column("episode_number", sa.Integer(), nullable=False),
        sa.Column("absolute_no", sa.Integer(), nullable=True),
        sa.Column("air_date", sa.Date(), nullable=True),
        sa.Column("monitored", sa.Boolean(), nullable=False),
        sa.Column("file_id", sa.Integer(), nullable=True),
        sa.UniqueConstraint(
            "title_id", "season_number", "episode_number", name="uq_episodes_title_id"
        ),
        sa.ForeignKeyConstraint(
            ["title_id", "season_number"],
            ["seasons.title_id", "seasons.season_number"],
            ondelete="CASCADE",
            name="fk_episodes_title_id_seasons",
        ),
        sa.ForeignKeyConstraint(
            ["file_id"],
            ["media_files.id"],
            ondelete="SET NULL",
            name="fk_episodes_file_id_media_files",
        ),
        sa.Index("ix_episodes_file_id", "file_id"),
    )


def downgrade() -> None:
    op.drop_table("episodes")
    op.drop_table("media_files")
    op.drop_table("seasons")
    op.drop_table("titles")
