"""Role, auth source enums and the User and AuthSession ORM models."""

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from all_togetharr.platform.db import Base, UtcDateTime


class Role(StrEnum):
    ADMIN = "admin"
    MANAGER = "manager"
    REQUESTER = "requester"
    VIEWER = "viewer"


class AuthSource(StrEnum):
    LOCAL = "local"
    JELLYFIN = "jellyfin"
    OIDC = "oidc"


class User(Base):
    __tablename__ = "users"

    __table_args__ = (
        CheckConstraint(
            "auth_source != 'local' OR password_hash IS NOT NULL",
            name="local_has_password",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    name_key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    role: Mapped[Role] = mapped_column(
        Enum(Role, name="role", native_enum=False, create_constraint=True,
             values_callable=lambda e: [m.value for m in e], length=20),
        nullable=False,
    )
    auth_source: Mapped[AuthSource] = mapped_column(
        Enum(AuthSource, name="auth_source", native_enum=False, create_constraint=True,
             values_callable=lambda e: [m.value for m in e], length=20),
        nullable=False,
        default=AuthSource.LOCAL,
    )
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, nullable=False, default=lambda: datetime.now(UTC)
    )


class AuthSession(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, nullable=False, default=lambda: datetime.now(UTC)
    )
    expires_at: Mapped[datetime] = mapped_column(
        UtcDateTime, nullable=False
    )
