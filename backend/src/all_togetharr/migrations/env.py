"""Alembic environment for database migrations."""

from alembic import context
from sqlalchemy import Connection

from all_togetharr.models import Base  # noqa: F401
from all_togetharr.platform.db import create_db_engine
from all_togetharr.platform.settings import Settings


def run_on(connection: Connection) -> None:
    """Run migrations on the given connection."""
    context.configure(
        connection=connection,
        target_metadata=Base.metadata,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    raise RuntimeError("Cannot run offline migrations in this setup.")

if context.config.attributes.get("connection") is not None:
    run_on(context.config.attributes["connection"])
else:
    engine = create_db_engine(Settings())
    try:
        with engine.begin() as connection:
            run_on(connection)
    finally:
        engine.dispose()
