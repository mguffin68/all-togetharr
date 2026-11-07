"""Catalog business logic."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from all_togetharr.catalog.models import Episode, Season, Title, TitleType
from all_togetharr.metadata.tmdb import TmdbClient


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
