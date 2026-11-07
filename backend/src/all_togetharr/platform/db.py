"""Database engine, session factory, and ORM base."""

from datetime import UTC, datetime
from pathlib import Path

from fastapi import Request
from sqlalchemy import DateTime, MetaData, TypeDecorator, create_engine, event, make_url
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase

from all_togetharr.platform.settings import Settings


class UtcDateTime(TypeDecorator[datetime]):
    """Store and return timezone-aware UTC datetimes.

    SQLite drops tzinfo on read-back; this re-attaches UTC.
    Naive values are rejected at write time.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(
        self, value: datetime | None, dialect
    ) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("UtcDateTime requires a timezone-aware value")
        return value.astimezone(UTC)

    def process_result_value(
        self, value: datetime | None, dialect
    ) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


def create_db_engine(settings: Settings) -> Engine:
    """Build a SQLAlchemy engine from settings and prime SQLite connections."""
    engine = create_engine(settings.database_url)

    if engine.dialect.name == "sqlite":
        db_path = make_url(settings.database_url).database
        if db_path and db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        @event.listens_for(engine, "connect")
        def set_pragmas(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def get_session(request: Request):
    """Yield a SQLAlchemy session and close it after the request."""
    factory = request.app.state.session_factory
    with factory() as session:
        yield session
