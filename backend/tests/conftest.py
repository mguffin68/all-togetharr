import logging

import pytest
from fastapi.testclient import TestClient

from all_togetharr.main import create_app
from all_togetharr.platform.settings import Settings

SETTINGS_ENV_VARS = ("CONFIG_DIR", "DATA_DIR", "DATABASE_URL", "LOG_LEVEL", "TZ", "COOKIE_SECURE")


@pytest.fixture(autouse=True)
def clean_settings_env(monkeypatch):
    """Keep the developer's shell environment out of every test."""
    for name in SETTINGS_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def restore_logging():
    """Undo any global logging changes made by the app during a test."""
    names = (None, "uvicorn", "uvicorn.error", "uvicorn.access", "httpx", "httpcore")
    loggers = [logging.getLogger(name) for name in names]
    saved = [(lg, lg.handlers[:], lg.level, lg.propagate, lg.disabled) for lg in loggers]
    yield
    for logger, handlers, level, propagate, disabled in saved:
        logger.handlers[:] = handlers
        logger.setLevel(level)
        logger.propagate = propagate
        logger.disabled = disabled


@pytest.fixture
def settings(tmp_path):
    return Settings(config_dir=tmp_path / "config", data_dir=tmp_path / "data")


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as test_client:
        yield test_client
