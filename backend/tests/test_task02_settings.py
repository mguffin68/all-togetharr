"""Task 2: settings from the environment, passed into the app."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from all_togetharr.main import create_app
from all_togetharr.platform.settings import Settings


def test_defaults_match_the_docker_layout():
    settings = Settings()

    assert settings.config_dir == Path("/config")
    assert settings.data_dir == Path("/data")
    assert settings.log_level == "INFO"
    assert settings.tz == "UTC"


def test_values_are_read_from_the_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("CONFIG_DIR", str(tmp_path / "c"))
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "d"))
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("TZ", "America/New_York")

    settings = Settings()

    assert settings.config_dir == tmp_path / "c"
    assert settings.data_dir == tmp_path / "d"
    assert settings.log_level == "DEBUG"
    assert settings.tz == "America/New_York"


def test_database_url_defaults_to_sqlite_in_default_config_dir():
    assert Settings().database_url == "sqlite:////config/all-togetharr.db"


def test_database_url_default_follows_config_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("CONFIG_DIR", str(tmp_path))

    assert Settings().database_url == f"sqlite:///{tmp_path}/all-togetharr.db"


def test_explicit_database_url_wins(monkeypatch):
    url = "postgresql+psycopg://user:pw@db/all_togetharr"
    monkeypatch.setenv("DATABASE_URL", url)

    assert Settings().database_url == url


def test_invalid_log_level_is_rejected(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "LOUD")

    with pytest.raises(ValidationError):
        Settings()


def test_lowercase_log_level_is_rejected(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "debug")

    with pytest.raises(ValidationError):
        Settings()


def test_database_url_default_survives_model_validate():
    assert Settings.model_validate({}).database_url == "sqlite:////config/all-togetharr.db"


def test_loading_settings_does_not_touch_the_disk(tmp_path):
    config_dir = tmp_path / "not-created"

    Settings(config_dir=config_dir)

    assert not config_dir.exists()


def test_create_app_stores_the_given_settings(settings):
    assert create_app(settings).state.settings is settings


def test_create_app_loads_settings_when_none_given(monkeypatch, tmp_path):
    monkeypatch.setenv("CONFIG_DIR", str(tmp_path))

    app = create_app()

    assert isinstance(app.state.settings, Settings)
    assert app.state.settings.config_dir == tmp_path
