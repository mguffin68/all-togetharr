"""Settings API routes (admin-only)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from all_togetharr.platform.auth.deps import require_role
from all_togetharr.platform.auth.models import Role
from all_togetharr.platform.db import get_session
from all_togetharr.platform.settings_store import (
    DEFINITIONS,
    SettingsStore,
)


def get_store(
    request: Request,
    db: Annotated[Session, Depends(get_session)],
) -> SettingsStore:
    return SettingsStore(db, request.app.state.secret_box)


def known_key(key: str) -> str:
    if key not in DEFINITIONS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Setting not found",
        )
    return key


class SettingResponse(BaseModel):
    key: str
    value: str | None
    secret: bool
    is_set: bool


class SettingUpdate(BaseModel):
    model_config = {"strict": True}

    value: str


def _build_response(store: SettingsStore, key: str) -> SettingResponse:
    definition = DEFINITIONS[key]
    is_set = store.is_set(key)

    if definition.secret:
        value = None
    else:
        value = store.get(key)

    return SettingResponse(
        key=key,
        value=value,
        secret=definition.secret,
        is_set=is_set,
    )


router = APIRouter(
    prefix="/api/v1/settings",
    tags=["settings"],
    dependencies=[Depends(require_role(Role.ADMIN))],
)


@router.get("", response_model=list[SettingResponse])
def list_settings(
    store: Annotated[SettingsStore, Depends(get_store)],
):
    return [_build_response(store, key) for key in DEFINITIONS]


@router.get("/{key}", response_model=SettingResponse)
def get_setting(
    key: Annotated[str, Depends(known_key)],
    store: Annotated[SettingsStore, Depends(get_store)],
):
    return _build_response(store, key)


@router.put("/{key}", response_model=SettingResponse)
def update_setting(
    key: Annotated[str, Depends(known_key)],
    update: SettingUpdate,
    store: Annotated[SettingsStore, Depends(get_store)],
    db: Annotated[Session, Depends(get_session)],
):
    try:
        store.set(key, update.value)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    db.commit()
    return _build_response(store, key)


@router.delete("/{key}", status_code=status.HTTP_204_NO_CONTENT)
def delete_setting(
    key: Annotated[str, Depends(known_key)],
    store: Annotated[SettingsStore, Depends(get_store)],
    db: Annotated[Session, Depends(get_session)],
):
    store.delete(key)
    db.commit()
