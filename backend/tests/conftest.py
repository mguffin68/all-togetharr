import pytest
from fastapi.testclient import TestClient

from all_togetharr.main import create_app
from all_togetharr.platform.settings import Settings

SETTINGS_ENV_VARS = ("CONFIG_DIR", "DATA_DIR", "DATABASE_URL", "LOG_LEVEL", "TZ")


@pytest.fixture(autouse=True)
def clean_settings_env(monkeypatch):
    """Keep the developer's shell environment out of every test."""
    for name in SETTINGS_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def settings(tmp_path):
    return Settings(config_dir=tmp_path / "config", data_dir=tmp_path / "data")


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as test_client:
        yield test_client
