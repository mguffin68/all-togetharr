"""TMDB API client with typed errors and frozen dataclasses."""

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

import httpx

from all_togetharr.catalog.models import TitleType
from all_togetharr.platform.settings_store import SettingsStore


class TmdbErrorKind(StrEnum):
    NOT_CONFIGURED = "not_configured"
    UNAUTHORIZED = "unauthorized"
    NOT_FOUND = "not_found"
    RATE_LIMITED = "rate_limited"
    NETWORK = "network"
    BAD_RESPONSE = "bad_response"


_ERROR_MESSAGES = {
    TmdbErrorKind.NOT_CONFIGURED: "TMDB API key is not configured",
    TmdbErrorKind.UNAUTHORIZED: "TMDB API authentication failed",
    TmdbErrorKind.NOT_FOUND: "TMDB resource not found",
    TmdbErrorKind.RATE_LIMITED: "TMDB API rate limit exceeded",
    TmdbErrorKind.NETWORK: "TMDB API network error",
    TmdbErrorKind.BAD_RESPONSE: "TMDB API returned an unexpected response",
}


class TmdbError(Exception):
    """Typed error for TMDB API failures."""

    def __init__(self, kind: TmdbErrorKind, retry_after: int | None = None) -> None:
        super().__init__(_ERROR_MESSAGES[kind])
        self.kind = kind
        self.retry_after = retry_after


@dataclass(frozen=True)
class SearchResult:
    tmdb_id: int
    type: TitleType
    name: str
    year: int | None
    overview: str
    poster_path: str | None


@dataclass(frozen=True)
class EpisodeDetails:
    season_number: int
    episode_number: int
    name: str
    air_date: date | None


@dataclass(frozen=True)
class SeasonDetails:
    season_number: int
    episodes: list[EpisodeDetails]


@dataclass(frozen=True)
class TitleDetails:
    tmdb_id: int
    type: TitleType
    name: str
    year: int | None
    overview: str
    poster_path: str | None
    imdb_id: str | None
    tvdb_id: int | None
    seasons: list[SeasonDetails]


_BASE_URL = "https://api.themoviedb.org/3"
_TIMEOUT = 10.0


@contextmanager
def _parsing():
    """Turn parse errors into BAD_RESPONSE."""
    try:
        yield
    except (KeyError, TypeError, ValueError, AttributeError):
        raise TmdbError(TmdbErrorKind.BAD_RESPONSE) from None


def _parse_int(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TmdbError(TmdbErrorKind.BAD_RESPONSE)
    return value


def _parse_str(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise TmdbError(TmdbErrorKind.BAD_RESPONSE)
    return value


def _parse_optional_str(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _parse_date(raw: object) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except (ValueError, AttributeError):
        raise TmdbError(TmdbErrorKind.BAD_RESPONSE) from None


def _common_fields(item: dict, title_type: TitleType) -> dict:
    name = _parse_str(item["title"] if title_type is TitleType.MOVIE else item["name"])
    date_key = "release_date" if title_type is TitleType.MOVIE else "first_air_date"
    year = _parse_date(item.get(date_key))
    if year is not None:
        year = year.year
    overview = item.get("overview")
    if not isinstance(overview, str):
        overview = ""
    return {
        "tmdb_id": _parse_int(item["id"]),
        "type": title_type,
        "name": name,
        "year": year,
        "overview": overview,
        "poster_path": _parse_optional_str(item.get("poster_path")),
    }


def _season(season_number: int, body: dict) -> SeasonDetails:
    episodes_raw = body.get("episodes")
    if not isinstance(episodes_raw, list):
        raise TmdbError(TmdbErrorKind.BAD_RESPONSE)
    episodes = [_episode(ep) for ep in episodes_raw]
    return SeasonDetails(season_number=season_number, episodes=episodes)


def _search_result(item: dict, title_type: TitleType) -> SearchResult:
    return SearchResult(**_common_fields(item, title_type))


def _episode(item: dict) -> EpisodeDetails:
    ep_season = _parse_int(item["season_number"])
    ep_number = _parse_int(item["episode_number"])
    ep_name = _parse_optional_str(item.get("name")) or ""
    ep_air = _parse_date(item.get("air_date"))
    return EpisodeDetails(
        season_number=ep_season, episode_number=ep_number,
        name=ep_name, air_date=ep_air,
    )


def _endpoint_type(title_type: TitleType) -> str:
    return "tv" if title_type is TitleType.SERIES else title_type.value


class TmdbClient:
    """TMDB API client with typed errors."""

    def __init__(
        self,
        api_key: str,
        language: str = "en-US",
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = httpx.Client(
            base_url=_BASE_URL,
            timeout=_TIMEOUT,
            follow_redirects=False,
            transport=transport,
        )
        self._params = {"api_key": api_key, "language": language}

    def __enter__(self) -> "TmdbClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def _get(self, path: str, **params: object) -> dict:
        """Send GET request and map every failure."""
        try:
            response = self._client.get(path, params={**self._params, **params})
        except httpx.HTTPError:
            raise TmdbError(TmdbErrorKind.NETWORK) from None
        return self._process(response)

    def _process(self, response: httpx.Response) -> dict:
        if response.status_code == 200:
            try:
                body = response.json()
            except (ValueError, TypeError):
                raise TmdbError(TmdbErrorKind.BAD_RESPONSE) from None
            if not isinstance(body, dict):
                raise TmdbError(TmdbErrorKind.BAD_RESPONSE)
            return body
        if response.status_code >= 500:
            raise TmdbError(TmdbErrorKind.NETWORK)
        if response.status_code == 401:
            raise TmdbError(TmdbErrorKind.UNAUTHORIZED)
        if response.status_code == 404:
            raise TmdbError(TmdbErrorKind.NOT_FOUND)
        if response.status_code == 429:
            retry_after_header = response.headers.get("Retry-After")
            retry_after: int | None = None
            if retry_after_header is not None:
                try:
                    retry_after = int(retry_after_header)
                except (ValueError, TypeError):
                    pass
            raise TmdbError(TmdbErrorKind.RATE_LIMITED, retry_after=retry_after)
        raise TmdbError(TmdbErrorKind.BAD_RESPONSE)

    def search(self, query: str, title_type: TitleType) -> list[SearchResult]:
        with _parsing():
            body = self._get(f"/search/{_endpoint_type(title_type)}", query=query)
            results = body.get("results")
            if not isinstance(results, list):
                raise TmdbError(TmdbErrorKind.BAD_RESPONSE)
            return [_search_result(item, title_type) for item in results]

    def details(self, tmdb_id: int, title_type: TitleType) -> TitleDetails:
        with _parsing():
            body = self._get(
                f"/{_endpoint_type(title_type)}/{tmdb_id}",
                append_to_response="external_ids",
            )
            fields = _common_fields(body, title_type)

            ext_ids = body.get("external_ids")
            if not isinstance(ext_ids, dict):
                raise TmdbError(TmdbErrorKind.BAD_RESPONSE)
            imdb_id = _parse_optional_str(ext_ids.get("imdb_id"))
            tvdb_raw = ext_ids.get("tvdb_id")
            tvdb_id = _parse_int(tvdb_raw) if tvdb_raw not in (None, "") else None

            seasons: list[SeasonDetails] = []
            if title_type is TitleType.SERIES:
                for season in body.get("seasons", []):
                    season_number = _parse_int(season["season_number"])
                    season_body = self._get(
                        f"/{_endpoint_type(title_type)}/{tmdb_id}/season/{season_number}",
                    )
                    seasons.append(_season(season_number, season_body))
            return TitleDetails(**fields, imdb_id=imdb_id, tvdb_id=tvdb_id, seasons=seasons)


def client_from_settings(
    store: SettingsStore,
    transport: httpx.BaseTransport | None = None,
) -> TmdbClient:
    api_key = store.get("tmdb.api_key")
    language = store.get("tmdb.language") or "en-US"
    if not api_key:
        raise TmdbError(TmdbErrorKind.NOT_CONFIGURED)
    return TmdbClient(api_key, language, transport=transport)
