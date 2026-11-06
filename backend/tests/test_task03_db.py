"""Task 3: database engine, request sessions and the health check."""

from typing import Annotated

from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from all_togetharr.main import create_app
from all_togetharr.platform.db import create_db_engine, get_session
from all_togetharr.platform.settings import Settings

DbSession = Annotated[Session, Depends(get_session)]


def pragma(connection, name):
    return connection.exec_driver_sql(f"PRAGMA {name}").scalar()


def track_closed_sessions(app):
    """Wrap the session factory and record each session that gets closed."""
    closed = []
    real_factory = app.state.session_factory

    def factory():
        session = real_factory()
        real_close = session.close

        def close():
            closed.append(session)
            real_close()

        session.close = close
        return session

    app.state.session_factory = factory
    return closed


def test_engine_creates_the_sqlite_file_in_a_missing_config_dir(settings):
    engine = create_db_engine(settings)

    with engine.connect():
        pass

    assert (settings.config_dir / "all-togetharr.db").exists()
    engine.dispose()


def test_engine_creates_the_folder_for_a_relative_sqlite_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    engine = create_db_engine(Settings(database_url="sqlite:///nested/relative.db"))

    with engine.connect():
        pass

    assert (tmp_path / "nested" / "relative.db").exists()
    engine.dispose()


def test_sqlite_uses_wal_mode(settings):
    engine = create_db_engine(settings)

    with engine.connect() as connection:
        assert pragma(connection, "journal_mode") == "wal"

    engine.dispose()


def test_every_sqlite_connection_enforces_foreign_keys(settings):
    engine = create_db_engine(settings)

    with engine.connect() as first, engine.connect() as second:
        assert pragma(first, "foreign_keys") == 1
        assert pragma(second, "foreign_keys") == 1

    engine.dispose()


def test_get_session_yields_a_working_session(settings):
    app = create_app(settings)

    @app.get("/probe")
    def probe(session: DbSession):
        return {"value": session.execute(text("select 1")).scalar_one()}

    with TestClient(app) as client:
        assert client.get("/probe").json() == {"value": 1}


def test_session_is_closed_after_the_request(settings):
    app = create_app(settings)
    closed = track_closed_sessions(app)

    @app.get("/probe")
    def probe(session: DbSession):
        return {"open": session not in closed}

    with TestClient(app) as client:
        assert client.get("/probe").json() == {"open": True}

    assert len(closed) == 1


def test_session_is_closed_when_the_route_raises(settings):
    app = create_app(settings)
    closed = track_closed_sessions(app)

    @app.get("/boom")
    def boom(session: DbSession):
        raise RuntimeError("boom")

    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get("/boom").status_code == 500

    assert len(closed) == 1


def test_engine_is_disposed_on_shutdown(settings, monkeypatch):
    app = create_app(settings)
    calls = []
    monkeypatch.setattr(app.state.engine, "dispose", lambda: calls.append(True))

    with TestClient(app):
        assert calls == []

    assert calls == [True]


def test_health_stays_ok_with_a_working_database(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_returns_503_when_the_database_is_unreachable(client):
    client.app.state.engine = create_engine("sqlite:////nonexistent-dir/broken.db")

    response = client.get("/api/health")

    assert response.status_code == 503
    assert response.json()["status"] == "error"
    assert "nonexistent-dir" not in response.text


def test_app_uses_the_configured_database(tmp_path):
    settings = Settings(config_dir=tmp_path, database_url=f"sqlite:///{tmp_path}/other.db")

    with TestClient(create_app(settings)) as client:
        assert client.get("/api/health").status_code == 200

    assert (tmp_path / "other.db").exists()
