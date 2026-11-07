"""Catalog business logic."""

from enum import StrEnum

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from all_togetharr.catalog.models import Episode, Season, Title, TitleStatus, TitleType
from all_togetharr.metadata.tmdb import TmdbClient


class TitleSort(StrEnum):
    NAME = "name"
    YEAR = "year"
    ADDED_AT = "added_at"


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"


class TitleExistsError(Exception):
    pass


def library_tmdb_ids(
    session: Session, title_type: TitleType, tmdb_ids: list[int]
) -> set[int]:
    stmt = (
        select(Title.tmdb_id)
        .where(Title.type == title_type)
        .where(Title.tmdb_id.in_(tmdb_ids))
    )
    return set(session.scalars(stmt).all())


def add_title(
    session: Session, tmdb: TmdbClient, tmdb_id: int, title_type: TitleType
) -> Title:
    exists_stmt = select(Title).where(
        Title.tmdb_id == tmdb_id, Title.type == title_type
    )
    if session.scalar(exists_stmt) is not None:
        raise TitleExistsError()

    details = tmdb.details(tmdb_id, title_type)

    title = Title(
        type=title_type,
        tmdb_id=details.tmdb_id,
        tvdb_id=details.tvdb_id,
        imdb_id=details.imdb_id,
        name=details.name,
        year=details.year,
        overview=details.overview,
        poster_path=details.poster_path,
    )

    for season_data in details.seasons:
        season = Season(season_number=season_data.season_number)
        for ep_data in season_data.episodes:
            ep = Episode(
                episode_number=ep_data.episode_number,
                name=ep_data.name,
                air_date=ep_data.air_date,
            )
            season.episodes.append(ep)
        title.seasons.append(season)

    session.add(title)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        if session.scalar(exists_stmt) is not None:
            raise TitleExistsError() from None
        raise

    return title


def list_titles(
    session: Session,
    *,
    page: int,
    page_size: int,
    title_type: TitleType | None = None,
    status: TitleStatus | None = None,
    q: str | None = None,
    sort: TitleSort = TitleSort.NAME,
    order: SortOrder = SortOrder.ASC,
) -> tuple[list[Title], int]:
    filters = []
    if title_type is not None:
        filters.append(Title.type == title_type)
    if status is not None:
        filters.append(Title.status == status)
    if q is not None:
        filters.append(Title.name.icontains(q, autoescape=True))

    count = session.scalar(select(func.count()).select_from(Title).where(*filters))

    column = {
        TitleSort.NAME: func.lower(Title.name),
        TitleSort.YEAR: Title.year,
        TitleSort.ADDED_AT: Title.added_at,
    }[sort]
    direction = column.desc() if order == SortOrder.DESC else column.asc()

    stmt = (
        select(Title)
        .where(*filters)
        .order_by(direction.nulls_last(), Title.id)
        .limit(page_size)
        .offset((page - 1) * page_size)
    )

    return list(session.scalars(stmt).all()), count


def get_title_with_episodes(session: Session, title_id: int) -> Title | None:
    stmt = (
        select(Title)
        .where(Title.id == title_id)
        .options(selectinload(Title.seasons).selectinload(Season.episodes))
    )
    return session.scalar(stmt)
