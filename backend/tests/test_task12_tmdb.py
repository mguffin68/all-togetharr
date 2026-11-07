"""Task 12: TMDB client. Every request goes to a fake transport, never to real TMDB."""

import json
import logging
from datetime import date
from pathlib import Path

import httpx
import pytest
from sqlalchemy.orm import sessionmaker

from all_togetharr.catalog.models import TitleType
from all_togetharr.metadata.tmdb import (
    EpisodeDetails,
    SearchResult,
    SeasonDetails,
    TitleDetails,
    TmdbClient,
    TmdbError,
    TmdbErrorKind,
    client_from_settings,
)
from all_togetharr.platform.db import create_db_engine
from all_togetharr.platform.migrations import run_migrations
from all_togetharr.platform.secrets import SecretBox, load_or_create_key
from all_togetharr.platform.settings_store import SettingsStore

FIXTURES = Path(__file__).parent / "fixtures" / "tmdb"
API_KEY = "test-api-key-do-not-leak"
ROUTES = {
    "/3/search/movie": "search_movie.json",
    "/3/search/tv": "search_tv.json",
    "/3/movie/603": "movie_603.json",
    "/3/tv/1396": "tv_1396.json",
    "/3/tv/1396/season/0": "tv_1396_season_0.json",
    "/3/tv/1396/season/1": "tv_1396_season_1.json",
}


def fixture(name):
    return json.loads((FIXTURES / name).read_text())


class FakeTmdb:
    """Replays fixtures and records each request."""

    def __init__(self):
        self.requests = []

    def __call__(self, request):
        self.requests.append(request)
        name = ROUTES.get(request.url.path)
        if name is None:
            return httpx.Response(404, json=fixture("error_404.json"))
        return httpx.Response(200, json=fixture(name))


def client_for(handler, **kwargs):
    return TmdbClient(API_KEY, transport=httpx.MockTransport(handler), **kwargs)


def failing_client(response):
    return client_for(lambda request: response)


def raising_client(exception):
    def handler(request):
        raise exception

    return client_for(handler)


@pytest.fixture
def fake():
    return FakeTmdb()


@pytest.fixture
def client(fake):
    with client_for(fake) as tmdb:
        yield tmdb


@pytest.fixture
def store(settings, tmp_path):
    engine = create_db_engine(settings)
    run_migrations(engine)
    with sessionmaker(bind=engine)() as session:
        yield SettingsStore(session, SecretBox(load_or_create_key(tmp_path / "keys")))
    engine.dispose()


def test_search_movies_returns_typed_results(client):
    results = client.search("matrix", TitleType.MOVIE)

    assert results[0] == SearchResult(
        tmdb_id=603,
        type=TitleType.MOVIE,
        name="The Matrix",
        year=1999,
        overview="A hacker learns what the world really is.",
        poster_path="/poster1.jpg",
    )


def test_search_handles_a_blank_release_date_and_no_poster(client):
    result = client.search("matrix", TitleType.MOVIE)[1]

    assert result.year is None
    assert result.poster_path is None


def test_search_series_returns_typed_results(client):
    results = client.search("breaking", TitleType.SERIES)

    assert results == [
        SearchResult(
            tmdb_id=1396,
            type=TitleType.SERIES,
            name="Breaking Bad",
            year=2008,
            overview="A chemistry teacher changes careers.",
            poster_path="/poster2.jpg",
        )
    ]


def test_search_sends_the_key_language_and_encoded_query(fake):
    with client_for(fake, language="de-DE") as tmdb:
        tmdb.search("fast & furious", TitleType.MOVIE)

    params = fake.requests[0].url.params
    assert fake.requests[0].url.host == "api.themoviedb.org"
    assert fake.requests[0].url.scheme == "https"
    assert params["query"] == "fast & furious"
    assert params["api_key"] == API_KEY
    assert params["language"] == "de-DE"


def test_language_defaults_to_en_us(client, fake):
    client.search("matrix", TitleType.MOVIE)

    assert fake.requests[0].url.params["language"] == "en-US"


def test_movie_details(client):
    details = client.details(603, TitleType.MOVIE)

    assert details == TitleDetails(
        tmdb_id=603,
        type=TitleType.MOVIE,
        name="The Matrix",
        year=1999,
        overview="A hacker learns what the world really is.",
        poster_path="/poster1.jpg",
        imdb_id="tt0133093",
        tvdb_id=None,
        seasons=[],
    )


def test_details_ask_for_external_ids_in_the_same_request(client, fake):
    client.details(603, TitleType.MOVIE)

    assert len(fake.requests) == 1
    assert fake.requests[0].url.params["append_to_response"] == "external_ids"


def test_series_details_include_seasons_and_episodes(client):
    details = client.details(1396, TitleType.SERIES)

    assert details.tmdb_id == 1396
    assert details.type is TitleType.SERIES
    assert details.name == "Breaking Bad"
    assert details.year == 2008
    assert details.imdb_id == "tt0903747"
    assert details.tvdb_id == 81189
    assert details.seasons == [
        SeasonDetails(
            season_number=0,
            episodes=[
                EpisodeDetails(
                    season_number=0,
                    episode_number=1,
                    name="Good Cop Bad Dog",
                    air_date=None,
                )
            ],
        ),
        SeasonDetails(
            season_number=1,
            episodes=[
                EpisodeDetails(
                    season_number=1,
                    episode_number=1,
                    name="Pilot",
                    air_date=date(2008, 1, 20),
                ),
                EpisodeDetails(
                    season_number=1,
                    episode_number=2,
                    name="Cat's in the Bag...",
                    air_date=date(2008, 1, 27),
                ),
            ],
        ),
    ]


def test_series_details_fetch_each_season_once(client, fake):
    client.details(1396, TitleType.SERIES)

    assert [request.url.path for request in fake.requests] == [
        "/3/tv/1396",
        "/3/tv/1396/season/0",
        "/3/tv/1396/season/1",
    ]


def test_blank_episode_air_date_is_none():
    payload = fixture("tv_1396_season_1.json")
    payload["episodes"][0]["air_date"] = ""

    def handler(request):
        if request.url.path == "/3/tv/1396/season/1":
            return httpx.Response(200, json=payload)
        return FakeTmdb()(request)

    with client_for(handler) as tmdb:
        details = tmdb.details(1396, TitleType.SERIES)

    assert details.seasons[1].episodes[0].air_date is None


@pytest.mark.parametrize(
    ("title_type", "fixture_name", "date_field"),
    [
        (TitleType.MOVIE, "search_movie.json", "release_date"),
        (TitleType.SERIES, "search_tv.json", "first_air_date"),
    ],
)
def test_search_result_with_no_date_field_has_no_year(title_type, fixture_name, date_field):
    payload = fixture(fixture_name)
    del payload["results"][0][date_field]

    with failing_client(httpx.Response(200, json=payload)) as tmdb:
        results = tmdb.search("anything", title_type)

    assert results[0].year is None


@pytest.mark.parametrize("name", ["", None])
def test_blank_episode_name_does_not_fail_the_series(name):
    payload = fixture("tv_1396_season_1.json")
    payload["episodes"][0]["name"] = name

    def handler(request):
        if request.url.path == "/3/tv/1396/season/1":
            return httpx.Response(200, json=payload)
        return FakeTmdb()(request)

    with client_for(handler) as tmdb:
        details = tmdb.details(1396, TitleType.SERIES)

    assert details.seasons[1].episodes[0].name == ""


def test_rate_limit_raises_a_typed_error_with_retry_after():
    response = httpx.Response(429, json=fixture("error_429.json"), headers={"Retry-After": "7"})

    with pytest.raises(TmdbError) as caught:
        failing_client(response).search("matrix", TitleType.MOVIE)

    assert caught.value.kind is TmdbErrorKind.RATE_LIMITED
    assert caught.value.retry_after == 7


@pytest.mark.parametrize("headers", [{}, {"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"}])
def test_rate_limit_without_usable_retry_after(headers):
    response = httpx.Response(429, json=fixture("error_429.json"), headers=headers)

    with pytest.raises(TmdbError) as caught:
        failing_client(response).search("matrix", TitleType.MOVIE)

    assert caught.value.kind is TmdbErrorKind.RATE_LIMITED
    assert caught.value.retry_after is None


@pytest.mark.parametrize(
    "exception",
    [
        httpx.ConnectError("connection refused"),
        httpx.ReadTimeout("timed out"),
        httpx.RemoteProtocolError("server disconnected"),
    ],
)
def test_network_failures_raise_the_typed_error(exception):
    with pytest.raises(TmdbError) as caught:
        raising_client(exception).search("matrix", TitleType.MOVIE)

    assert caught.value.kind is TmdbErrorKind.NETWORK


@pytest.mark.parametrize("status", [500, 502, 503])
def test_server_errors_count_as_network_failures(status):
    with pytest.raises(TmdbError) as caught:
        failing_client(httpx.Response(status, text="bad")).search("matrix", TitleType.MOVIE)

    assert caught.value.kind is TmdbErrorKind.NETWORK


def test_bad_api_key_raises_the_typed_error():
    response = httpx.Response(401, json=fixture("error_401.json"))

    with pytest.raises(TmdbError) as caught:
        failing_client(response).search("matrix", TitleType.MOVIE)

    assert caught.value.kind is TmdbErrorKind.UNAUTHORIZED


def test_unknown_title_raises_not_found(client):
    with pytest.raises(TmdbError) as caught:
        client.details(1, TitleType.MOVIE)

    assert caught.value.kind is TmdbErrorKind.NOT_FOUND


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, text="<html>not json</html>"),
        httpx.Response(200, json=["not", "an", "object"]),
        httpx.Response(200, json={"page": 1}),
        httpx.Response(200, json={"results": [{"title": "No id"}]}),
        httpx.Response(200, json={"results": [{"id": 1, "title": "x", "release_date": "soon"}]}),
        httpx.Response(302, headers={"Location": "https://example.com/"}),
    ],
)
def test_unexpected_responses_raise_bad_response(response):
    with pytest.raises(TmdbError) as caught:
        failing_client(response).search("matrix", TitleType.MOVIE)

    assert caught.value.kind is TmdbErrorKind.BAD_RESPONSE


def test_series_with_a_bad_season_payload_raises_bad_response():
    def handler(request):
        if request.url.path == "/3/tv/1396/season/1":
            return httpx.Response(200, json={"episodes": [{"name": "No number"}]})
        return FakeTmdb()(request)

    with client_for(handler) as tmdb, pytest.raises(TmdbError) as caught:
        tmdb.details(1396, TitleType.SERIES)

    assert caught.value.kind is TmdbErrorKind.BAD_RESPONSE


@pytest.mark.parametrize(
    "tmdb",
    [
        raising_client(httpx.ConnectError(f"failed: /3/search/movie?api_key={API_KEY}")),
        failing_client(httpx.Response(500, text=f"echo {API_KEY}")),
        failing_client(httpx.Response(200, text=f"not json {API_KEY}")),
    ],
)
def test_errors_never_carry_the_api_key(tmdb, caplog):
    caplog.set_level(logging.DEBUG, logger="all_togetharr")

    with pytest.raises(TmdbError) as caught:
        tmdb.search("matrix", TitleType.MOVIE)

    assert API_KEY not in str(caught.value)
    assert API_KEY not in repr(caught.value)
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__ or caught.value.__context__ is None
    assert API_KEY not in caplog.text


def test_client_from_settings_uses_the_stored_key_and_language(store, fake):
    store.set("tmdb.api_key", "stored-key")
    store.set("tmdb.language", "fr-FR")

    with client_from_settings(store, transport=httpx.MockTransport(fake)) as tmdb:
        tmdb.search("matrix", TitleType.MOVIE)

    assert fake.requests[0].url.params["api_key"] == "stored-key"
    assert fake.requests[0].url.params["language"] == "fr-FR"


def test_client_from_settings_needs_a_key(store):
    with pytest.raises(TmdbError) as caught:
        client_from_settings(store)

    assert caught.value.kind is TmdbErrorKind.NOT_CONFIGURED


def test_client_closes_its_http_connection(fake):
    class ClosableTransport(httpx.MockTransport):
        closed = False

        def close(self):
            self.closed = True

    transport = ClosableTransport(fake)

    with TmdbClient(API_KEY, transport=transport):
        pass

    assert transport.closed


def test_httpx_is_a_runtime_dependency():
    pyproject = (Path(__file__).parent.parent / "pyproject.toml").read_text()
    runtime = pyproject.split("[dependency-groups]")[0]

    assert '"httpx' in runtime
