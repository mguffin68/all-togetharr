"""FastAPI dependencies for authentication and role checks."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from all_togetharr.platform.auth.models import Role, User
from all_togetharr.platform.auth.sessions import SESSION_COOKIE, get_session_user
from all_togetharr.platform.db import get_session

ROLE_RANKS = {
    Role.VIEWER: 0,
    Role.REQUESTER: 1,
    Role.MANAGER: 2,
    Role.ADMIN: 3,
}


def get_current_user(
    request: Request,
    db: Annotated[Session, Depends(get_session)],
) -> User:
    cookie = request.cookies.get(SESSION_COOKIE)
    if not cookie:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    user = get_session_user(db, cookie)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return user


def require_role(role: Role):
    def _checker(
        user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if ROLE_RANKS[user.role] < ROLE_RANKS[role]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role",
            )
        return user

    return _checker
