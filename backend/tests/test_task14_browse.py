"""Task 14: browse the catalog."""

import time
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import event, insert

from all_togetharr.catalog.models import Episode, Season, Title, TitleStatus, TitleType
from all_togetharr.platform.auth.models import Role
from all_togetharr.platform.auth.users import create_user

PASSWORD = "correct horse battery"
TITLES_URL = "/api/v1/titles"
START = datetime(2026, 1, 1, tzinfo=UTC)


def login_as(client, role=Role.VIEWER, name="Mike"):
    with client.app.state.session_factory() as db_session:
        create_user(db_session, name, role, password=PASSWORD)
        db_session.commit()
    response = client.post("/api/v1/auth/login", json={"name": name, "password": PASSWORD})
    assert response.status_code == 200


@pytest.fixture
def api(client):
    login_as(client)
    return client


@pytest.fixture
def session(client):
    with client.app.state.session_factory() as db_session:
        yield db_session


def seed(session):
    """Store four titles with known names, types, statuses, years and dates."""
    rows = [
        ("alpha", TitleType.MOVIE, TitleStatus.REQUESTED, 2001, 3),
        ("Bravo", TitleType.SERIES, TitleStatus.AVAILABLE, 1999, 1),
        ("charlie 100%", TitleType.MOVIE, TitleStatus.AVAILABLE, None, 2),
        ("Delta_Force", TitleType.SERIES, TitleStatus.REQUESTED, 2010, 4),
    ]
    for tmdb_id, (name, title_type, status, year, day) in enumerate(rows, start=1):
        session.add(
            Title(
                type=title_type,
                tmdb_id=tmdb_id,
                name=name,
                status=status,
                year=year,
                added_at=START + timedelta(days=day),
            )
        )
    session.commit()


def names(response):
    assert response.status_code == 200
    return [item["name"] for item in response.json()["items"]]


def add_series(session, seasons=1, tmdb_id=500):
    title = Title(type=TitleType.SERIES, tmdb_id=tmdb_id, name=f"Series {tmdb_id}")
    for season_number in range(seasons):
        season = Season(season_number=season_number)
        season.episodes.append(
            Episode(episode_number=2, name="Second", air_date=date(2026, 1, 2))
        )
        season.episodes.append(Episode(episode_number=1, name="First"))
        title.seasons.append(season)
    session.add(title)
    session.commit()
    return title.id


def test_empty_library(api):
    response = api.get(TITLES_URL)

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "page": 1, "page_size": 50}


def test_list_item_shape(api, session):
    seed(session)

    item = api.get(TITLES_URL).json()["items"][0]

    assert item["name"] == "alpha"
    assert item["type"] == "movie"
    assert item["status"] == "requested"
    assert item["year"] == 2001
    assert item["tags"] == []
    assert datetime.fromisoformat(item["added_at"]) == START + timedelta(days=3)
    assert "seasons" not in item


def test_default_sort_is_name_ignoring_case(api, session):
    seed(session)

    assert names(api.get(TITLES_URL)) == ["alpha", "Bravo", "charlie 100%", "Delta_Force"]


def test_sort_descending(api, session):
    seed(session)

    response = api.get(TITLES_URL, params={"sort": "name", "order": "desc"})

    assert names(response) == ["Delta_Force", "charlie 100%", "Bravo", "alpha"]


def test_sort_by_added_at(api, session):
    seed(session)

    response = api.get(TITLES_URL, params={"sort": "added_at", "order": "desc"})

    assert names(response) == ["Delta_Force", "alpha", "charlie 100%", "Bravo"]


@pytest.mark.parametrize(
    ("order", "expected"),
    [
        ("asc", ["Bravo", "alpha", "Delta_Force", "charlie 100%"]),
        ("desc", ["Delta_Force", "alpha", "Bravo", "charlie 100%"]),
    ],
)
def test_sort_by_year_puts_unknown_years_last(api, session, order, expected):
    seed(session)

    assert names(api.get(TITLES_URL, params={"sort": "year", "order": order})) == expected


def test_equal_sort_values_page_in_a_stable_order(api, session):
    for tmdb_id in range(1, 7):
        session.add(Title(type=TitleType.MOVIE, tmdb_id=tmdb_id, name="Same"))
    session.commit()

    ids = []
    for page in (1, 2, 3):
        body = api.get(TITLES_URL, params={"page": page, "page_size": 2}).json()
        ids += [item["id"] for item in body["items"]]

    assert ids == sorted(ids)
    assert len(set(ids)) == 6


def test_paging(api, session):
    seed(session)

    body = api.get(TITLES_URL, params={"page": 2, "page_size": 3}).json()

    assert [item["name"] for item in body["items"]] == ["Delta_Force"]
    assert body["total"] == 4
    assert body["page"] == 2
    assert body["page_size"] == 3


def test_page_past_the_end_is_empty(api, session):
    seed(session)

    body = api.get(TITLES_URL, params={"page": 9}).json()

    assert body["items"] == []
    assert body["total"] == 4


def test_filter_by_type(api, session):
    seed(session)

    response = api.get(TITLES_URL, params={"type": "series"})

    assert names(response) == ["Bravo", "Delta_Force"]
    assert response.json()["total"] == 2


def test_filter_by_status(api, session):
    seed(session)

    assert names(api.get(TITLES_URL, params={"status": "available"})) == [
        "Bravo",
        "charlie 100%",
    ]


def test_filters_combine(api, session):
    seed(session)

    response = api.get(TITLES_URL, params={"type": "movie", "status": "available", "q": "char"})

    assert names(response) == ["charlie 100%"]
    assert response.json()["total"] == 1


def test_text_search_ignores_case(api, session):
    seed(session)

    assert names(api.get(TITLES_URL, params={"q": "BRAV"})) == ["Bravo"]


@pytest.mark.parametrize(("query", "expected"), [("%", ["charlie 100%"]), ("_", ["Delta_Force"])])
def test_text_search_treats_wildcards_as_plain_text(api, session, query, expected):
    seed(session)

    assert names(api.get(TITLES_URL, params={"q": query})) == expected


@pytest.mark.parametrize(
    "params",
    [
        {"page": 0},
        {"page": 10**30},
        {"page_size": 0},
        {"page_size": 201},
        {"type": "collection"},
        {"status": "wanted"},
        {"sort": "password"},
        {"order": "sideways"},
        {"q": "x" * 201},
    ],
)
def test_list_rejects_bad_parameters(api, params):
    assert api.get(TITLES_URL, params=params).status_code == 422


def test_title_detail_includes_ordered_seasons_and_episodes(api, session):
    title_id = add_series(session, seasons=2)

    response = api.get(f"{TITLES_URL}/{title_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == title_id
    assert body["name"] == "Series 500"
    assert [season["season_number"] for season in body["seasons"]] == [0, 1]
    assert body["seasons"][0]["monitored"] is True
    episodes = body["seasons"][0]["episodes"]
    assert [episode["episode_number"] for episode in episodes] == [1, 2]
    assert episodes[0]["name"] == "First"
    assert episodes[0]["air_date"] is None
    assert episodes[1]["air_date"] == "2026-01-02"
    assert episodes[0]["monitored"] is True
    assert episodes[0]["absolute_no"] is None
    assert episodes[0]["file_id"] is None


def test_movie_detail_has_no_seasons(api, session):
    seed(session)
    title_id = api.get(TITLES_URL).json()["items"][0]["id"]

    assert api.get(f"{TITLES_URL}/{title_id}").json()["seasons"] == []


def test_unknown_title_returns_404(api):
    assert api.get(f"{TITLES_URL}/999").status_code == 404


@pytest.mark.parametrize("title_id", ["0", "abc", str(2**31), str(10**30)])
def test_detail_rejects_bad_ids(api, title_id):
    assert api.get(f"{TITLES_URL}/{title_id}").status_code == 422


def count_queries(client, url):
    statements = []

    def record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    engine = client.app.state.engine
    event.listen(engine, "before_cursor_execute", record)
    try:
        assert client.get(url).status_code == 200
    finally:
        event.remove(engine, "before_cursor_execute", record)
    return len(statements)


def test_detail_query_count_does_not_grow_with_seasons(api, session):
    small = add_series(session, seasons=1, tmdb_id=501)
    large = add_series(session, seasons=6, tmdb_id=502)

    assert count_queries(api, f"{TITLES_URL}/{small}") == count_queries(
        api, f"{TITLES_URL}/{large}"
    )


def test_list_query_count_does_not_grow_with_titles(api, session):
    session.add(Title(type=TitleType.MOVIE, tmdb_id=1, name="First"))
    session.commit()
    one_title = count_queries(api, TITLES_URL)

    session.add_all(
        [Title(type=TitleType.MOVIE, tmdb_id=number, name="More") for number in range(2, 12)]
    )
    session.commit()

    assert count_queries(api, TITLES_URL) == one_title


def test_list_never_loads_seasons(api, session):
    add_series(session, seasons=3)
    statements = []

    def record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    engine = api.app.state.engine
    event.listen(engine, "before_cursor_execute", record)
    try:
        api.get(TITLES_URL)
    finally:
        event.remove(engine, "before_cursor_execute", record)

    assert not [statement for statement in statements if "FROM seasons" in statement]


def test_browse_needs_login(client):
    assert client.get(TITLES_URL).status_code == 401
    assert client.get(f"{TITLES_URL}/1").status_code == 401


def test_listing_10000_titles_takes_under_a_second(api, session):
    rows = [
        {
            "type": TitleType.MOVIE if number % 2 else TitleType.SERIES,
            "tmdb_id": number,
            "name": f"Title {number:05d}",
            "year": 1950 + number % 70,
        }
        for number in range(1, 10_001)
    ]
    session.execute(insert(Title), rows)
    session.commit()

    started = time.perf_counter()
    response = api.get(TITLES_URL, params={"q": "title", "sort": "year", "page": 100})
    elapsed = time.perf_counter() - started

    assert response.status_code == 200
    assert response.json()["total"] == 10_000
    assert len(response.json()["items"]) == 50
    assert elapsed < 1
