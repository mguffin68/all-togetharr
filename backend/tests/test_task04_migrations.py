"""Task 4: Alembic migrations run on startup and match the models."""

import logging
import os
import subprocess
import sys
from pathlib import Path

import pytest
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
from sqlalchemy import Column, Integer, MetaData, Table, create_engine, inspect, text
from sqlalchemy.exc import OperationalError

import all_togetharr.models  # noqa: F401  (registers every model on Base.metadata)
from all_togetharr.main import create_app
from all_togetharr.platform.db import Base, create_db_engine
from all_togetharr.platform.migrations import alembic_config, run_migrations

BACKEND_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture
def engine(settings):
    db_engine = create_db_engine(settings)
    yield db_engine
    db_engine.dispose()


def head_revision():
    return ScriptDirectory.from_config(alembic_config()).get_current_head()


def current_revision(engine):
    with engine.connect() as connection:
        return MigrationContext.configure(connection).get_current_revision()


def schema_snapshot(engine):
    with engine.connect() as connection:
        schema = connection.execute(
            text("select type, name, sql from sqlite_master order by name")
        ).all()
        versions = connection.execute(text("select version_num from alembic_version")).all()
    return schema, versions


def schema_drift(engine, metadata):
    with engine.connect() as connection:
        return compare_metadata(MigrationContext.configure(connection), metadata)


def test_migrations_have_exactly_one_head():
    assert len(ScriptDirectory.from_config(alembic_config()).get_heads()) == 1


def test_alembic_ini_points_at_the_same_migrations():
    ini_config = Config(str(BACKEND_DIR / "alembic.ini"))

    assert ScriptDirectory.from_config(ini_config).get_current_head() == head_revision()


def test_app_startup_migrates_the_configured_database(settings):
    app = create_app(settings)

    with TestClient(app):
        assert "alembic_version" in inspect(app.state.engine).get_table_names()
        assert current_revision(app.state.engine) == head_revision()


def test_running_migrations_twice_changes_nothing(engine):
    run_migrations(engine)
    before = schema_snapshot(engine)

    run_migrations(engine)

    assert schema_snapshot(engine) == before


def test_restarting_the_app_changes_nothing(settings, engine):
    with TestClient(create_app(settings)):
        pass
    before = schema_snapshot(engine)

    with TestClient(create_app(settings)):
        pass

    assert schema_snapshot(engine) == before


def test_models_and_migrations_match(engine):
    run_migrations(engine)

    assert schema_drift(engine, Base.metadata) == []


def test_drift_check_catches_a_table_with_no_migration(engine):
    run_migrations(engine)
    metadata = MetaData()
    Table("not_migrated", metadata, Column("id", Integer, primary_key=True))

    assert schema_drift(engine, metadata) != []


def test_base_names_constraints_consistently():
    assert {"ix", "uq", "ck", "fk", "pk"} <= set(Base.metadata.naming_convention)


def test_failed_migration_stops_startup(settings):
    app = create_app(settings)
    app.state.engine = create_engine("sqlite:////nonexistent-dir/broken.db")

    with pytest.raises(OperationalError):
        with TestClient(app):
            pass


def test_migrations_leave_existing_loggers_enabled(engine):
    logger = logging.getLogger("all_togetharr.task04")

    run_migrations(engine)

    assert not logger.disabled


def test_alembic_cli_uses_the_environment_settings(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env={**os.environ, "CONFIG_DIR": str(tmp_path)},
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    cli_engine = create_engine(f"sqlite:///{tmp_path}/all-togetharr.db")
    assert current_revision(cli_engine) == head_revision()
    cli_engine.dispose()
