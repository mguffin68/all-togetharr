"""Task 13: search TMDB and add titles. TMDB is always a fake transport."""

import json
from datetime import date
from pathlib import Path

import httpx
import pytest
from alembic import command
from sqlalchemy import func, inspect, select
from sqlalchemy.exc import IntegrityError

from all_togetharr.catalog.models import Episode, Season, Title, TitleStatus, TitleType
from all_togetharr.catalog.routes import get_tmdb_client
from all_togetharr.catalog.service import TitleExistsError, add_title, library_tmdb_ids
from all_togetharr.metadata.tmdb import TmdbClient
from all_togetharr.platform.auth.models import Role
from all_togetharr.platform.auth.users import create_user
from all_togetharr.platform.migrations import alembic_config

FIXTURES = Path(__file__).parent / "fixtures" / "tmdb"
PASSWORD = "correct horse battery"
SEARCH_URL = "/api/v1/search/metadata"
TITLES_URL = "/api/v1/titles"
ROUTES = {
    "/3/search/movie": "search_movie.json",
    "/3/search/tv": "search_tv.json",
    "/3/movie/603": "movie_603.json",
    "/3/tv/1396": "tv_1396.json",
    "/3/tv/1396/season/0": "tv_1396_season_0.json",
    "/3/tv/1396/season/1": "tv_1396_season_1.json",
}
MOVIE = {"tmdb_id": 603, "type": "movie"}
SERIES = {"tmdb_id": 1396, "type": "series"}


def fixture(name):
    return json.loads((FIXTURES / name).read_text())


class FakeTmdb:
    """Replays fixtures. Tests can set `response` or `before_reply` to change behaviour."""

    def __init__(self):
        self.requests = []
        self.response = None
        self.before_reply = None

    def __call__(self, request):
        self.requests.append(request)
        if self.before_reply is not None:
            self.before_reply(request)
        if self.response is not None:
            return self.response
        name = ROUTES.get(request.url.path)
        if name is None:
            return httpx.Response(404, json=fixture("error_404.json"))
        return httpx.Response(200, json=fixture(name))


@pytest.fixture
def fake():
    return FakeTmdb()


@pytest.fixture
def tmdb(fake):
    with TmdbClient("key", transport=httpx.MockTransport(fake)) as tmdb_client:
        yield tmdb_client


@pytest.fixture
def api(client, tmdb):
    """App client with TMDB replaced by the fake."""
    client.app.dependency_overrides[get_tmdb_client] = lambda: tmdb
    yield client
    client.app.dependency_overrides.clear()


@pytest.fixture
def session(client):
    with client.app.state.session_factory() as db_session:
        yield db_session


def login_as(client, role=Role.MANAGER, name="Mike"):
    with client.app.state.session_factory() as db_session:
        create_user(db_session, name, role, password=PASSWORD)
        db_session.commit()
    response = client.post("/api/v1/auth/login", json={"name": name, "password": PASSWORD})
    assert response.status_code == 200


def count(session, model):
    return session.scalar(select(func.count()).select_from(model))


def store_title(session, tmdb_id, title_type):
    session.add(Title(type=title_type, tmdb_id=tmdb_id, name="Stored"))
    session.commit()


def test_search_returns_results_marked_not_in_library(api):
    login_as(api)

    response = api.get(SEARCH_URL, params={"query": "matrix", "type": "movie"})

    assert response.status_code == 200
    assert response.json()[0] == {
        "tmdb_id": 603,
        "type": "movie",
        "name": "The Matrix",
        "year": 1999,
        "overview": "A hacker learns what the world really is.",
        "poster_path": "/poster1.jpg",
        "in_library": False,
    }


def test_search_marks_titles_already_in_the_library(api, session):
    login_as(api)
    store_title(session, 603, TitleType.MOVIE)

    results = api.get(SEARCH_URL, params={"query": "matrix", "type": "movie"}).json()

    assert [(item["tmdb_id"], item["in_library"]) for item in results] == [
        (603, True),
        (999001, False),
    ]


def test_same_tmdb_id_of_the_other_type_is_not_in_the_library(api, session):
    login_as(api)
    store_title(session, 603, TitleType.SERIES)

    results = api.get(SEARCH_URL, params={"query": "matrix", "type": "movie"}).json()

    assert results[0]["in_library"] is False


def test_search_without_a_type_returns_movies_then_series(api, fake):
    login_as(api)

    results = api.get(SEARCH_URL, params={"query": "x"}).json()

    assert [item["type"] for item in results] == ["movie", "movie", "series"]
    assert [request.url.path for request in fake.requests] == ["/3/search/movie", "/3/search/tv"]


@pytest.mark.parametrize(
    "params",
    [{}, {"query": ""}, {"query": "x" * 201}, {"query": "x", "type": "collection"}],
)
def test_search_rejects_bad_parameters(api, fake, params):
    login_as(api)

    assert api.get(SEARCH_URL, params=params).status_code == 422
    assert fake.requests == []


def test_search_needs_login(api):
    assert api.get(SEARCH_URL, params={"query": "x"}).status_code == 401


def test_viewer_cannot_search(api, fake):
    login_as(api, Role.VIEWER)

    assert api.get(SEARCH_URL, params={"query": "x"}).status_code == 403
    assert fake.requests == []


def test_requester_can_search(api):
    login_as(api, Role.REQUESTER)

    assert api.get(SEARCH_URL, params={"query": "x"}).status_code == 200


def test_add_movie(api, session):
    login_as(api)

    response = api.post(TITLES_URL, json=MOVIE)

    assert response.status_code == 201
    body = response.json()
    assert body["type"] == "movie"
    assert body["tmdb_id"] == 603
    assert body["imdb_id"] == "tt0133093"
    assert body["tvdb_id"] is None
    assert body["name"] == "The Matrix"
    assert body["year"] == 1999
    assert body["overview"] == "A hacker learns what the world really is."
    assert body["poster_path"] == "/poster1.jpg"
    assert body["status"] == "requested"
    assert body["monitored"] is True
    assert body["tags"] == []
    stored = session.get(Title, body["id"])
    assert stored.status is TitleStatus.REQUESTED
    assert stored.overview == "A hacker learns what the world really is."
    assert stored.poster_path == "/poster1.jpg"
    assert count(session, Season) == 0


def test_add_series_stores_seasons_and_episodes(api, session):
    login_as(api)

    response = api.post(TITLES_URL, json=SERIES)

    assert response.status_code == 201
    assert response.json()["tvdb_id"] == 81189
    stored = session.get(Title, response.json()["id"])
    assert [season.season_number for season in stored.seasons] == [0, 1]
    pilot = stored.seasons[1].episodes[0]
    assert pilot.title_id == stored.id
    assert pilot.season_number == 1
    assert pilot.episode_number == 1
    assert pilot.name == "Pilot"
    assert pilot.air_date == date(2008, 1, 20)
    assert count(session, Episode) == 3


def test_adding_the_same_title_twice_returns_409(api, session, fake):
    login_as(api)
    api.post(TITLES_URL, json=MOVIE)
    calls = len(fake.requests)

    response = api.post(TITLES_URL, json=MOVIE)

    assert response.status_code == 409
    assert len(fake.requests) == calls
    assert count(session, Title) == 1


def test_two_adds_racing_still_return_409(api, session, fake):
    login_as(api)

    def other_request_wins(request):
        fake.before_reply = None
        with api.app.state.session_factory() as other_session:
            store_title(other_session, 603, TitleType.MOVIE)

    fake.before_reply = other_request_wins

    response = api.post(TITLES_URL, json=MOVIE)

    assert response.status_code == 409
    assert count(session, Title) == 1


def test_unknown_tmdb_id_returns_404(api, session):
    login_as(api)

    response = api.post(TITLES_URL, json={"tmdb_id": 1, "type": "movie"})

    assert response.status_code == 404
    assert count(session, Title) == 0


def test_failed_season_fetch_stores_nothing(api, session, fake):
    login_as(api)

    def fail_on_season(request):
        if "/season/1" in request.url.path:
            fake.response = httpx.Response(500, text="bad")

    fake.before_reply = fail_on_season

    assert api.post(TITLES_URL, json=SERIES).status_code == 502
    assert count(session, Title) == 0
    assert count(session, Season) == 0


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"tmdb_id": 603},
        {"tmdb_id": 0, "type": "movie"},
        {"tmdb_id": -1, "type": "movie"},
        {"tmdb_id": 2**31, "type": "movie"},
        {"tmdb_id": 603, "type": "collection"},
    ],
)
def test_add_rejects_bad_bodies(api, fake, body):
    login_as(api)

    assert api.post(TITLES_URL, json=body).status_code == 422
    assert fake.requests == []


def test_add_needs_login(api):
    assert api.post(TITLES_URL, json=MOVIE).status_code == 401


@pytest.mark.parametrize("role", [Role.VIEWER, Role.REQUESTER])
def test_only_managers_and_admins_can_add(api, fake, role):
    login_as(api, role)

    assert api.post(TITLES_URL, json=MOVIE).status_code == 403
    assert fake.requests == []


def test_admin_can_add(api):
    login_as(api, Role.ADMIN)

    assert api.post(TITLES_URL, json=MOVIE).status_code == 201


@pytest.mark.parametrize(
    ("status", "headers", "expected", "code"),
    [
        (401, {}, 502, "unauthorized"),
        (429, {"Retry-After": "7"}, 503, "rate_limited"),
        (500, {}, 502, "network"),
        (302, {"Location": "https://example.com/"}, 502, "bad_response"),
    ],
)
def test_tmdb_failures_map_to_http_errors(api, fake, status, headers, expected, code):
    login_as(api)
    fake.response = httpx.Response(status, json={}, headers=headers)

    response = api.get(SEARCH_URL, params={"query": "x", "type": "movie"})

    assert response.status_code == expected
    assert response.json()["code"] == code


def test_rate_limit_passes_retry_after_to_the_caller(api, fake):
    login_as(api)
    fake.response = httpx.Response(429, json={}, headers={"Retry-After": "7"})

    response = api.get(SEARCH_URL, params={"query": "x", "type": "movie"})

    assert response.headers["retry-after"] == "7"


def test_missing_api_key_returns_503_without_calling_tmdb(client):
    login_as(client)

    response = client.get(SEARCH_URL, params={"query": "x"})

    assert response.status_code == 503
    assert response.json()["code"] == "not_configured"


def test_missing_api_key_does_not_outrank_the_login_check(client):
    assert client.get(SEARCH_URL, params={"query": "x"}).status_code == 401


def test_library_tmdb_ids_only_returns_matches_of_that_type(session):
    session.add_all(
        [
            Title(type=TitleType.MOVIE, tmdb_id=1, name="A"),
            Title(type=TitleType.MOVIE, tmdb_id=2, name="B"),
            Title(type=TitleType.SERIES, tmdb_id=3, name="C"),
        ]
    )
    session.flush()

    assert library_tmdb_ids(session, TitleType.MOVIE, [1, 3, 4]) == {1}


def test_add_title_raises_when_the_title_exists(session, tmdb):
    store_title(session, 603, TitleType.MOVIE)

    with pytest.raises(TitleExistsError):
        add_title(session, tmdb, 603, TitleType.MOVIE)


def test_add_title_flushes_and_leaves_the_commit_to_the_caller(session, tmdb):
    title = add_title(session, tmdb, 603, TitleType.MOVIE)

    assert title.id is not None
    session.rollback()
    assert count(session, Title) == 0


def test_integrity_errors_that_are_not_duplicates_are_not_hidden(session, fake, tmdb):
    def duplicate_episode(request):
        if request.url.path == "/3/tv/1396/season/1":
            payload = fixture("tv_1396_season_1.json")
            payload["episodes"][1]["episode_number"] = 1
            fake.response = httpx.Response(200, json=payload)
        else:
            fake.response = None

    fake.before_reply = duplicate_episode

    with pytest.raises(IntegrityError):
        add_title(session, tmdb, 1396, TitleType.SERIES)


def test_episode_uses_the_season_it_was_fetched_for(session, fake, tmdb):
    def wrong_season_number(request):
        if request.url.path == "/3/tv/1396/season/1":
            payload = fixture("tv_1396_season_1.json")
            payload["episodes"][0]["season_number"] = 7
            fake.response = httpx.Response(200, json=payload)
        else:
            fake.response = None

    fake.before_reply = wrong_season_number

    title = add_title(session, tmdb, 1396, TitleType.SERIES)

    assert title.seasons[1].episodes[0].season_number == 1


def test_migration_0007_downgrades_and_upgrades_cleanly(client, settings, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", settings.database_url)
    config = alembic_config()
    engine = client.app.state.engine

    command.downgrade(config, "0006_catalog")
    assert "overview" not in {item["name"] for item in inspect(engine).get_columns("titles")}

    command.upgrade(config, "head")
    assert "overview" in {item["name"] for item in inspect(engine).get_columns("titles")}
    assert "name" in {item["name"] for item in inspect(engine).get_columns("episodes")}
