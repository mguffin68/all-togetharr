"""User creation and validation."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from all_togetharr.platform.auth.models import AuthSource, Role, User
from all_togetharr.platform.auth.passwords import hash_password

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 1024
MAX_NAME_LENGTH = 100


class UserExistsError(ValueError):
    pass


def create_user(
    session: Session,
    name: str,
    role: Role,
    *,
    password: str | None = None,
    auth_source: AuthSource = AuthSource.LOCAL,
) -> User:
    trimmed = name.strip()
    if not trimmed:
        raise ValueError("name must not be blank")
    if len(trimmed) > MAX_NAME_LENGTH:
        raise ValueError("name exceeds maximum length")

    name_key = trimmed.casefold()
    if len(name_key) > MAX_NAME_LENGTH:
        raise ValueError("name_key exceeds maximum length")

    if auth_source == AuthSource.LOCAL and password is None:
        raise ValueError("local user must have a password")
    if auth_source != AuthSource.LOCAL and password is not None:
        raise ValueError("non-local user must not have a password")

    if password is not None:
        if len(password) < MIN_PASSWORD_LENGTH or len(password) > MAX_PASSWORD_LENGTH:
            raise ValueError(
                f"password must be between "
                f"{MIN_PASSWORD_LENGTH} and {MAX_PASSWORD_LENGTH} characters"
            )

    existing = session.scalar(
        select(User.id).where(User.name_key == name_key)
    )
    if existing is not None:
        raise UserExistsError(f"user '{name_key}' already exists")

    hashed = hash_password(password) if password is not None else None

    user = User(
        name=trimmed,
        name_key=name_key,
        role=role,
        auth_source=auth_source,
        password_hash=hashed,
    )
    session.add(user)
    session.flush()
    return user
