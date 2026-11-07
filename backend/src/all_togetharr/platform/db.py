"""Database engine, session factory, and ORM base."""

from pathlib import Path

from fastapi import Request
from sqlalchemy import MetaData, create_engine, event, make_url
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase

from all_togetharr.platform.settings import Settings


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
