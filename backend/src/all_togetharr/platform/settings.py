"""Application settings loaded from environment variables."""

from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration derived from environment variables."""

    model_config = SettingsConfigDict(env_prefix="")

    config_dir: Path = Path("/config")
    data_dir: Path = Path("/data")
    database_url: str = ""
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    tz: str = "UTC"
    cookie_secure: bool = False
    static_dir: Path | None = None

    @model_validator(mode="after")
    def _build_database_url(self) -> "Settings":
        if not self.database_url:
            self.database_url = f"sqlite:///{self.config_dir / 'all-togetharr.db'}"
        return self
