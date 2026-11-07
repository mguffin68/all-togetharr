"""Task 11: catalog models for titles, seasons, episodes and media files."""

import subprocess
import sys
from datetime import UTC, date, datetime

import pytest
from alembic import command
from sqlalchemy import BigInteger, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from all_togetharr.catalog.models import (
    Episode,
    MediaFile,
    Season,
    Title,
    TitleStatus,
    TitleType,
)
from all_togetharr.platform.db import create_db_engine
from all_togetharr.platform.migrations import alembic_config, run_migrations

CATALOG_TABLES = {"titles", "seasons", "episodes", "media_files"}
BIG_FILE_SIZE = 80 * 1024**3


@pytest.fixture
def engine(settings):
    db_engine = create_db_engine(settings)
    run_migrations(db_engine)
    yield db_engine
    db_engine.dispose()


@pytest.fixture
def session(engine):
    with sessionmaker(bind=engine)() as db_session:
        yield db_session


def make_title(**overrides):
    values = {"type": TitleType.SERIES, "tmdb_id": 1399, "name": "Example Show"}
    return Title(**(values | overrides))


def make_file(title, path="/media/example/file.mkv", **overrides):
    values = {"title_id": title.id, "path": path, "size": 1024}
    return MediaFile(**(values | overrides))


def add_series(session):
    """Store a series with one season and one episode."""
    title = make_title()
    session.add(title)
    session.flush()
    season = Season(title_id=title.id, season_number=1)
    session.add(season)
    session.flush()
    episode = Episode(title_id=title.id, season_number=1, episode_number=1)
    session.add(episode)
    session.flush()
    return title, season, episode


def count(session, model):
    return len(session.scalars(select(model)).all())


def test_title_status_values_are_the_prd_pipeline():
    assert [status.value for status in TitleStatus] == [
        "requested",
        "approved",
        "searching",
        "downloading",
        "importing",
        "available",
    ]


def test_title_type_values():
    assert {title_type.value for title_type in TitleType} == {"movie", "series"}


def test_title_stores_every_prd_field(session):
    title = make_title(
        tvdb_id=121361,
        imdb_id="tt0944947",
        year=2011,
        status=TitleStatus.DOWNLOADING,
        monitored=False,
        quality_profile_id=3,
        root_folder_id=4,
        tags=["family", "4k"],
    )
    session.add(title)
    session.commit()
    session.expire_all()

    stored = session.get(Title, title.id)
    assert stored.type is TitleType.SERIES
    assert stored.tmdb_id == 1399
    assert stored.tvdb_id == 121361
    assert stored.imdb_id == "tt0944947"
    assert stored.name == "Example Show"
    assert stored.year == 2011
    assert stored.status is TitleStatus.DOWNLOADING
    assert stored.monitored is False
    assert stored.quality_profile_id == 3
    assert stored.root_folder_id == 4
    assert stored.tags == ["family", "4k"]


def test_title_defaults(session):
    title = make_title()
    session.add(title)
    session.commit()
    session.expire_all()

    stored = session.get(Title, title.id)
    assert stored.status is TitleStatus.REQUESTED
    assert stored.monitored is True
    assert stored.tags == []
    assert stored.tvdb_id is None
    assert stored.imdb_id is None
    assert stored.year is None
    assert stored.quality_profile_id is None
    assert stored.root_folder_id is None
    assert stored.added_at.tzinfo is not None
    assert stored.added_at <= datetime.now(UTC)


def test_default_tags_are_not_shared_between_titles(session):
    first = make_title(tmdb_id=1)
    second = make_title(tmdb_id=2)
    session.add_all([first, second])
    session.flush()

    assert first.tags is not second.tags


@pytest.mark.parametrize("field", ["type", "tmdb_id", "name"])
def test_title_required_fields(session, field):
    values = {"type": TitleType.MOVIE, "tmdb_id": 1, "name": "Example"}
    del values[field]
    session.add(Title(**values))

    with pytest.raises(IntegrityError):
        session.flush()


def insert_raw_title(session, *, title_type="movie", status="requested"):
    session.execute(
        text(
            "insert into titles (type, tmdb_id, name, status, monitored, tags, added_at) "
            "values (:type, 1, 'Example', :status, 1, '[]', '2026-01-01 00:00:00')"
        ),
        {"type": title_type, "status": status},
    )


def test_raw_insert_helper_accepts_valid_values(session):
    insert_raw_title(session)

    assert count(session, Title) == 1


def test_database_rejects_a_status_outside_the_pipeline(session):
    with pytest.raises(IntegrityError):
        insert_raw_title(session, status="wanted")


def test_database_rejects_an_unknown_type(session):
    with pytest.raises(IntegrityError):
        insert_raw_title(session, title_type="collection")


def test_same_tmdb_id_and_type_is_rejected(session):
    session.add(make_title(type=TitleType.MOVIE))
    session.flush()
    session.add(make_title(type=TitleType.MOVIE))

    with pytest.raises(IntegrityError):
        session.flush()


def test_same_tmdb_id_with_a_different_type_is_allowed(session):
    session.add_all([make_title(type=TitleType.MOVIE), make_title(type=TitleType.SERIES)])
    session.flush()

    assert count(session, Title) == 2


def test_season_and_episode_store_prd_fields(session):
    title, season, episode = add_series(session)
    file = make_file(title)
    session.add(file)
    session.flush()
    episode.absolute_no = 12
    episode.air_date = date(2026, 1, 2)
    episode.monitored = False
    episode.file_id = file.id
    session.commit()
    session.expire_all()

    stored = session.get(Episode, episode.id)
    assert stored.title_id == title.id
    assert stored.season_number == 1
    assert stored.episode_number == 1
    assert stored.absolute_no == 12
    assert stored.air_date == date(2026, 1, 2)
    assert stored.monitored is False
    assert stored.file_id == file.id
    assert stored.file.path == file.path
    assert session.get(Season, season.id).monitored is True


def test_season_zero_holds_specials(session):
    title = make_title()
    session.add(title)
    session.flush()
    session.add(Season(title_id=title.id, season_number=0))
    session.flush()
    session.add(Episode(title_id=title.id, season_number=0, episode_number=0))
    session.flush()

    assert count(session, Episode) == 1


def test_episode_optional_fields_default_to_empty(session):
    _, _, episode = add_series(session)
    session.commit()
    session.expire_all()

    stored = session.get(Episode, episode.id)
    assert stored.absolute_no is None
    assert stored.air_date is None
    assert stored.file_id is None
    assert stored.monitored is True


def test_duplicate_season_is_rejected(session):
    title, _, _ = add_series(session)
    session.add(Season(title_id=title.id, season_number=1))

    with pytest.raises(IntegrityError):
        session.flush()


def test_duplicate_episode_is_rejected(session):
    title, _, _ = add_series(session)
    session.add(Episode(title_id=title.id, season_number=1, episode_number=1))

    with pytest.raises(IntegrityError):
        session.flush()


def test_episode_needs_an_existing_season(session):
    title, _, _ = add_series(session)
    session.add(Episode(title_id=title.id, season_number=2, episode_number=1))

    with pytest.raises(IntegrityError):
        session.flush()


def test_season_needs_an_existing_title(session):
    session.add(Season(title_id=999, season_number=1))

    with pytest.raises(IntegrityError):
        session.flush()


def test_title_lists_its_seasons_and_season_lists_its_episodes(session):
    title, season, episode = add_series(session)
    session.commit()
    session.expire_all()

    stored = session.get(Title, title.id)
    assert [item.id for item in stored.seasons] == [season.id]
    assert [item.id for item in stored.seasons[0].episodes] == [episode.id]


def test_media_file_stores_prd_fields(session):
    title = make_title()
    session.add(title)
    session.flush()
    file = make_file(
        title,
        size=BIG_FILE_SIZE,
        quality="Bluray-2160p",
        custom_format_score=-150,
        mediainfo={"video": {"codec": "hevc"}, "audio": [{"language": "eng"}]},
        jellyfin_item_id="abc123",
        link_key="2049:987654321",
    )
    session.add(file)
    session.commit()
    session.expire_all()

    stored = session.get(MediaFile, file.id)
    assert stored.title_id == title.id
    assert stored.path == "/media/example/file.mkv"
    assert stored.size == BIG_FILE_SIZE
    assert stored.quality == "Bluray-2160p"
    assert stored.custom_format_score == -150
    assert stored.mediainfo == {"video": {"codec": "hevc"}, "audio": [{"language": "eng"}]}
    assert stored.jellyfin_item_id == "abc123"
    assert stored.link_key == "2049:987654321"


def test_media_file_defaults(session):
    title = make_title()
    session.add(title)
    session.flush()
    file = make_file(title)
    session.add(file)
    session.commit()
    session.expire_all()

    stored = session.get(MediaFile, file.id)
    assert stored.quality is None
    assert stored.custom_format_score == 0
    assert stored.mediainfo is None
    assert stored.jellyfin_item_id is None
    assert stored.link_key is None


def test_media_file_size_column_holds_files_over_2_gib():
    assert isinstance(MediaFile.__table__.c.size.type, BigInteger)


def test_media_file_path_is_unique(session):
    title = make_title()
    session.add(title)
    session.flush()
    session.add(make_file(title))
    session.flush()
    session.add(make_file(title))

    with pytest.raises(IntegrityError):
        session.flush()


def test_hardlinked_files_can_share_a_link_key(session):
    title = make_title()
    session.add(title)
    session.flush()
    session.add_all(
        [
            make_file(title, path="/downloads/file.mkv", link_key="2049:1"),
            make_file(title, path="/media/file.mkv", link_key="2049:1"),
        ]
    )
    session.flush()

    assert count(session, MediaFile) == 2


def test_one_file_can_cover_several_episodes(session):
    title, _, first = add_series(session)
    second = Episode(title_id=title.id, season_number=1, episode_number=2)
    file = make_file(title)
    session.add_all([second, file])
    session.flush()
    first.file_id = file.id
    second.file_id = file.id
    session.flush()

    assert first.file_id == second.file_id


def test_deleting_a_file_keeps_the_episode_and_clears_its_link(session):
    title, _, episode = add_series(session)
    file = make_file(title)
    session.add(file)
    session.flush()
    episode.file_id = file.id
    session.commit()

    session.delete(file)
    session.commit()
    session.expire_all()

    assert session.get(Episode, episode.id).file_id is None


def test_deleting_a_title_removes_its_catalog_rows(session):
    title, _, episode = add_series(session)
    file = make_file(title)
    session.add(file)
    session.flush()
    episode.file_id = file.id
    session.commit()

    session.delete(title)
    session.commit()

    for model in (Title, Season, Episode, MediaFile):
        assert count(session, model) == 0


def test_database_cascades_when_a_title_row_is_deleted(session):
    title, _, _ = add_series(session)
    session.add(make_file(title))
    session.commit()
    title_id = title.id
    session.expunge_all()

    session.execute(text("delete from titles where id = :id"), {"id": title_id})
    session.commit()

    for model in (Season, Episode, MediaFile):
        assert count(session, model) == 0


def test_episode_and_season_relationship_stays_in_sync(session):
    title, season, _ = add_series(session)
    session.commit()
    session.expire_all()
    stored = session.get(Season, season.id)
    episode = Episode(title_id=title.id, season_number=1, episode_number=2, season=stored)
    session.add(episode)

    assert episode in stored.episodes


@pytest.mark.parametrize("table", sorted(CATALOG_TABLES))
def test_migration_sets_no_database_defaults(engine, table):
    columns = inspect(engine).get_columns(table)

    assert [column["name"] for column in columns if column["default"] is not None] == []


def test_title_check_constraints_are_not_duplicated(engine):
    names = {item["name"] for item in inspect(engine).get_check_constraints("titles")}

    assert names == {"ck_titles_title_type", "ck_titles_title_status"}


def test_migration_downgrades_and_upgrades_cleanly(engine, settings, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", settings.database_url)
    config = alembic_config()

    command.downgrade(config, "0005_settings")
    assert not CATALOG_TABLES & set(inspect(engine).get_table_names())

    command.upgrade(config, "head")
    assert CATALOG_TABLES <= set(inspect(engine).get_table_names())


def test_catalog_models_register_in_a_fresh_process():
    code = (
        "from all_togetharr.models import Base\n"
        f"missing = {CATALOG_TABLES!r} - set(Base.metadata.tables)\n"
        "raise SystemExit(str(missing) if missing else 0)\n"
    )

    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)

    assert result.returncode == 0, result.stderr
