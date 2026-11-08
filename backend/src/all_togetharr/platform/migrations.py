"""Alembic migration helpers."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.engine import Engine


def alembic_config() -> Config:
    """Build an Alembic Config entirely in code (no alembic.ini needed)."""
    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
    config = Config()
    config.set_main_option("script_location", str(migrations_dir))
    return config


def run_migrations(engine: Engine) -> None:
    """Upgrade the given engine to the latest migration head."""
    config = alembic_config()

    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
