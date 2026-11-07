"""Session creation, lookup and deletion."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.responses import Response

from all_togetharr.platform.auth.models import AuthSession, User

SESSION_COOKIE = "all_togetharr_session"
SESSION_LIFETIME = timedelta(days=30)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def set_session_cookie(response: Response, request: Request, token: str):
    secure = request.app.state.settings.cookie_secure
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        samesite="lax",
        path="/",
        max_age=int(SESSION_LIFETIME.total_seconds()),
        secure=secure,
    )


def clear_session_cookie(response: Response, request: Request):
    secure = request.app.state.settings.cookie_secure
    response.delete_cookie(
        SESSION_COOKIE,
        httponly=True,
        samesite="lax",
        path="/",
        secure=secure,
    )


def create_session(db: Session, user: User) -> str:
    token = secrets.token_urlsafe(32)
    token_hash = _hash_token(token)
    now = datetime.now(UTC)
    session = AuthSession(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=now + SESSION_LIFETIME,
    )
    db.add(session)
    db.flush()
    return token


def get_session_user(db: Session, token: str) -> User | None:
    token_hash = _hash_token(token)
    now = datetime.now(UTC)
    auth_session = db.scalar(
        select(AuthSession)
        .where(AuthSession.token_hash == token_hash)
        .where(AuthSession.expires_at > now)
    )
    if auth_session is None:
        return None
    return db.get(User, auth_session.user_id)


def delete_session(db: Session, token: str) -> None:
    token_hash = _hash_token(token)
    auth_session = db.scalar(
        select(AuthSession).where(AuthSession.token_hash == token_hash)
    )
    if auth_session is not None:
        db.delete(auth_session)
        db.flush()
