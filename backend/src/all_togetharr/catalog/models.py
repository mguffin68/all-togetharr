"""Title, season, episode and media-file ORM models."""

from datetime import UTC, date, datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
    BigInteger,
    Date,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from all_togetharr.platform.db import Base, UtcDateTime


class TitleType(StrEnum):
    MOVIE = "movie"
    SERIES = "series"


class TitleStatus(StrEnum):
    REQUESTED = "requested"
    APPROVED = "approved"
    SEARCHING = "searching"
    DOWNLOADING = "downloading"
    IMPORTING = "importing"
    AVAILABLE = "available"


class Title(Base):
    __tablename__ = "titles"

    __table_args__ = (
        UniqueConstraint("tmdb_id", "type", name="uq_titles_tmdb_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[TitleType] = mapped_column(
        Enum(TitleType, name="title_type", native_enum=False, create_constraint=True,
             values_callable=lambda e: [m.value for m in e], length=20),
        nullable=False,
    )
    tmdb_id: Mapped[int] = mapped_column(Integer, nullable=False)
    tvdb_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    imdb_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[TitleStatus] = mapped_column(
        Enum(TitleStatus, name="title_status", native_enum=False, create_constraint=True,
             values_callable=lambda e: [m.value for m in e], length=20),
        nullable=False,
        default=TitleStatus.REQUESTED,
    )
    monitored: Mapped[bool] = mapped_column(nullable=False, default=True)
    quality_profile_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    root_folder_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    added_at: Mapped[datetime] = mapped_column(
        UtcDateTime, nullable=False, default=lambda: datetime.now(UTC)
    )

    seasons: Mapped[list["Season"]] = relationship(
        "Season",
        back_populates="title",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Season.season_number",
    )
    files: Mapped[list["MediaFile"]] = relationship(
        "MediaFile",
        back_populates="title",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Season(Base):
    __tablename__ = "seasons"

    __table_args__ = (
        UniqueConstraint("title_id", "season_number", name="uq_seasons_title_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title_id: Mapped[int] = mapped_column(
        ForeignKey("titles.id", ondelete="CASCADE"), nullable=False
    )
    season_number: Mapped[int] = mapped_column(Integer, nullable=False)
    monitored: Mapped[bool] = mapped_column(nullable=False, default=True)

    title: Mapped["Title"] = relationship("Title", back_populates="seasons")
    episodes: Mapped[list["Episode"]] = relationship(
        "Episode",
        back_populates="season",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Episode.episode_number",
    )


class MediaFile(Base):
    __tablename__ = "media_files"

    __table_args__ = (
        Index("ix_media_files_link_key", "link_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title_id: Mapped[int] = mapped_column(
        ForeignKey("titles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    path: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    quality: Mapped[str | None] = mapped_column(String(100), nullable=True)
    custom_format_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mediainfo: Mapped[dict | None] = mapped_column(JSON(none_as_null=True), nullable=True)
    jellyfin_item_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    link_key: Mapped[str | None] = mapped_column(String(64), nullable=True)

    title: Mapped["Title"] = relationship("Title", back_populates="files")
    episodes: Mapped[list["Episode"]] = relationship(
        "Episode",
        back_populates="file",
    )


class Episode(Base):
    __tablename__ = "episodes"

    __table_args__ = (
        ForeignKeyConstraint(
            ["title_id", "season_number"],
            ["seasons.title_id", "seasons.season_number"],
            ondelete="CASCADE",
            name="fk_episodes_title_id_seasons",
        ),
        Index("ix_episodes_file_id", "file_id"),
        UniqueConstraint(
            "title_id", "season_number", "episode_number", name="uq_episodes_title_id"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title_id: Mapped[int] = mapped_column(Integer, nullable=False)
    season_number: Mapped[int] = mapped_column(Integer, nullable=False)
    episode_number: Mapped[int] = mapped_column(Integer, nullable=False)
    absolute_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    air_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    monitored: Mapped[bool] = mapped_column(nullable=False, default=True)
    file_id: Mapped[int | None] = mapped_column(
        ForeignKey("media_files.id", ondelete="SET NULL"), nullable=True
    )

    season: Mapped["Season"] = relationship(
        "Season",
        back_populates="episodes",
    )
    file: Mapped["MediaFile | None"] = relationship(
        "MediaFile",
        back_populates="episodes",
    )
