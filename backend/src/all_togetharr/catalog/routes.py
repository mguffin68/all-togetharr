"""Catalog API routes: search TMDB and add titles."""

from collections.abc import Iterator
from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from all_togetharr.catalog.models import TitleStatus, TitleType
from all_togetharr.catalog.service import (
    SortOrder,
    TitleExistsError,
    TitleSort,
    add_title,
    get_title_with_episodes,
    library_tmdb_ids,
    list_titles,
)
from all_togetharr.metadata.tmdb import TmdbClient, TmdbError, TmdbErrorKind, client_from_settings
from all_togetharr.platform.auth.deps import require_role
from all_togetharr.platform.auth.models import Role
from all_togetharr.platform.db import get_session
from all_togetharr.platform.settings_store import SettingsStore


def get_tmdb_client(
    request: Request,
    db: Annotated[Session, Depends(get_session)],
) -> Iterator[TmdbClient]:
    store = SettingsStore(db, request.app.state.secret_box)
    with client_from_settings(store) as client:
        yield client


class SearchItemResponse(BaseModel):
    tmdb_id: int
    type: TitleType
    name: str
    year: int | None
    overview: str
    poster_path: str | None
    in_library: bool


class TitleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: TitleType
    tmdb_id: int
    tvdb_id: int | None
    imdb_id: str | None
    name: str
    year: int | None
    overview: str | None
    poster_path: str | None
    status: TitleStatus
    monitored: bool
    tags: list[str]
    added_at: datetime


class EpisodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    season_number: int
    episode_number: int
    name: str | None
    absolute_no: int | None
    air_date: date | None
    monitored: bool
    file_id: int | None


class SeasonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    season_number: int
    monitored: bool
    episodes: list[EpisodeResponse]


class TitleDetailResponse(TitleResponse):
    seasons: list[SeasonResponse]


class TitleListResponse(BaseModel):
    items: list[TitleResponse]
    total: int
    page: int
    page_size: int


class AddTitleBody(BaseModel):
    tmdb_id: int = Field(gt=0, le=2147483647)
    type: TitleType


router = APIRouter(prefix="/api/v1", tags=["catalog"])


@router.get(
    "/search/metadata",
    response_model=list[SearchItemResponse],
    dependencies=[Depends(require_role(Role.REQUESTER))],
)
def search_metadata(
    tmdb: Annotated[TmdbClient, Depends(get_tmdb_client)],
    db: Annotated[Session, Depends(get_session)],
    query: Annotated[str, Query(min_length=1, max_length=200)],
    type: TitleType | None = None,
):
    types_to_search: list[TitleType]
    if type is not None:
        types_to_search = [type]
    else:
        types_to_search = [TitleType.MOVIE, TitleType.SERIES]

    all_results: list[SearchItemResponse] = []
    for t in types_to_search:
        results = tmdb.search(query, t)
        tmdb_id_list = [r.tmdb_id for r in results]
        in_lib = library_tmdb_ids(db, t, tmdb_id_list)
        for r in results:
            all_results.append(SearchItemResponse(
                tmdb_id=r.tmdb_id,
                type=r.type,
                name=r.name,
                year=r.year,
                overview=r.overview,
                poster_path=r.poster_path,
                in_library=r.tmdb_id in in_lib,
            ))
    return all_results


@router.post(
    "/titles",
    response_model=TitleResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(Role.MANAGER))],
)
def add_title_route(
    body: AddTitleBody,
    tmdb: Annotated[TmdbClient, Depends(get_tmdb_client)],
    db: Annotated[Session, Depends(get_session)],
):
    try:
        title = add_title(db, tmdb, body.tmdb_id, body.type)
    except TitleExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Title already in library",
        ) from None
    db.commit()
    return TitleResponse.model_validate(title)


@router.get(
    "/titles",
    response_model=TitleListResponse,
    dependencies=[Depends(require_role(Role.VIEWER))],
)
def list_titles_route(
    db: Annotated[Session, Depends(get_session)],
    page: Annotated[int, Query(ge=1, le=1_000_000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
    type: TitleType | None = None,
    status_param: Annotated[TitleStatus | None, Query(alias="status")] = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
    sort: TitleSort = TitleSort.NAME,
    order: SortOrder = SortOrder.ASC,
):
    titles, total = list_titles(
        db, page=page, page_size=page_size,
        title_type=type, status=status_param, q=q,
        sort=sort, order=order,
    )
    return TitleListResponse(
        items=[TitleResponse.model_validate(t) for t in titles],
        total=total, page=page, page_size=page_size,
    )


@router.get(
    "/titles/{title_id}",
    response_model=TitleDetailResponse,
    dependencies=[Depends(require_role(Role.VIEWER))],
)
def get_title_route(
    title_id: Annotated[int, Path(gt=0, le=2147483647)],
    db: Annotated[Session, Depends(get_session)],
):
    title = get_title_with_episodes(db, title_id)
    if title is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Title not found")
    return TitleDetailResponse.model_validate(title)


def tmdb_error_handler(request: Request, exc: TmdbError) -> JSONResponse:
    status_map = {
        TmdbErrorKind.NOT_FOUND: status.HTTP_404_NOT_FOUND,
        TmdbErrorKind.NOT_CONFIGURED: status.HTTP_503_SERVICE_UNAVAILABLE,
        TmdbErrorKind.RATE_LIMITED: status.HTTP_503_SERVICE_UNAVAILABLE,
        TmdbErrorKind.UNAUTHORIZED: status.HTTP_502_BAD_GATEWAY,
        TmdbErrorKind.NETWORK: status.HTTP_502_BAD_GATEWAY,
        TmdbErrorKind.BAD_RESPONSE: status.HTTP_502_BAD_GATEWAY,
    }
    http_status = status_map[exc.kind]
    body = {"detail": str(exc), "code": exc.kind}
    response = JSONResponse(status_code=http_status, content=body)
    if exc.retry_after is not None:
        response.headers["retry-after"] = str(exc.retry_after)
    return response
