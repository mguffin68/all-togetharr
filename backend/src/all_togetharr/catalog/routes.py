"""Catalog API routes: search TMDB and add titles."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from all_togetharr.catalog.models import TitleType
from all_togetharr.catalog.service import TitleExistsError, add_title, library_tmdb_ids
from all_togetharr.metadata.tmdb import TmdbClient, TmdbError, TmdbErrorKind, client_from_settings
from all_togetharr.platform.auth.deps import require_role
from all_togetharr.platform.auth.models import Role
from all_togetharr.platform.db import get_session
from all_togetharr.platform.settings_store import SettingsStore


def get_tmdb_client(
    request: Request,
    db: Annotated[Session, Depends(get_session)],
) -> TmdbClient:
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
    id: int
    type: TitleType
    tmdb_id: int
    tvdb_id: int | None
    imdb_id: str | None
    name: str
    year: int | None
    overview: str | None
    poster_path: str | None
    status: str
    monitored: bool
    tags: list
    added_at: str


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
    query: str = Query(min_length=1, max_length=200),
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
    return TitleResponse(
        id=title.id,
        type=title.type,
        tmdb_id=title.tmdb_id,
        tvdb_id=title.tvdb_id,
        imdb_id=title.imdb_id,
        name=title.name,
        year=title.year,
        overview=title.overview,
        poster_path=title.poster_path,
        status=title.status.value,
        monitored=title.monitored,
        tags=title.tags,
        added_at=title.added_at.isoformat(),
    )


def tmdb_error_handler(request: Request, exc: TmdbError) -> JSONResponse:

    status_map = {
        TmdbErrorKind.NOT_FOUND: status.HTTP_404_NOT_FOUND,
        TmdbErrorKind.NOT_CONFIGURED: status.HTTP_503_SERVICE_UNAVAILABLE,
        TmdbErrorKind.RATE_LIMITED: status.HTTP_503_SERVICE_UNAVAILABLE,
        TmdbErrorKind.UNAUTHORIZED: status.HTTP_502_BAD_GATEWAY,
        TmdbErrorKind.NETWORK: status.HTTP_502_BAD_GATEWAY,
        TmdbErrorKind.BAD_RESPONSE: status.HTTP_502_BAD_GATEWAY,
    }
    http_status = status_map.get(exc.kind, status.HTTP_502_BAD_GATEWAY)
    body = {"detail": str(exc), "code": exc.kind}
    response = JSONResponse(status_code=http_status, content=body)
    if exc.retry_after is not None:
        response.headers["retry-after"] = str(exc.retry_after)
    return response
