"""Authentication routes: setup, login, logout, me."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, StringConstraints
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from all_togetharr.platform.auth.deps import get_current_user
from all_togetharr.platform.auth.models import Role, User
from all_togetharr.platform.auth.sessions import (
    SESSION_COOKIE,
    clear_session_cookie,
    create_session,
    delete_session,
    set_session_cookie,
)
from all_togetharr.platform.auth.users import (
    MAX_NAME_LENGTH,
    MAX_PASSWORD_LENGTH,
    authenticate,
    create_user,
)
from all_togetharr.platform.db import get_session


class Credentials(BaseModel):
    name: Annotated[
        str,
        StringConstraints(max_length=MAX_NAME_LENGTH),
    ]
    password: Annotated[
        str,
        StringConstraints(max_length=MAX_PASSWORD_LENGTH),
    ]


class UserResponse(BaseModel):
    id: int
    name: str
    role: str
    auth_source: str

    model_config = {"from_attributes": True}


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/setup")
def get_setup(db: Annotated[Session, Depends(get_session)]):
    count = db.scalar(select(func.count()).select_from(User))
    return {"required": count == 0}


@router.post("/setup", status_code=201, response_model=UserResponse)
def post_setup(
    req: Credentials,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_session)],
):
    count = db.scalar(select(func.count()).select_from(User))
    if count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Already configured",
        )

    try:
        user = create_user(
            db, req.name, Role.ADMIN, password=req.password
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    token = create_session(db, user)
    db.commit()
    set_session_cookie(response, request, token)
    return user


@router.post("/login", response_model=UserResponse)
def post_login(
    req: Credentials,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_session)],
):
    user = authenticate(db, req.name, req.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid name or password",
        )

    token = create_session(db, user)
    db.commit()
    set_session_cookie(response, request, token)
    return user


@router.post("/logout")
def post_logout(
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_session)],
):
    cookie = request.cookies.get(SESSION_COOKIE)
    if cookie is not None:
        delete_session(db, cookie)
        db.commit()
    clear_session_cookie(response, request)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserResponse)
def get_me(user: Annotated[User, Depends(get_current_user)]):
    return user
