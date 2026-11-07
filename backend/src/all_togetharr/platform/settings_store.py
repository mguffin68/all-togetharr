"""Encrypted settings store backed by the database."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, Session, mapped_column

from all_togetharr.platform.db import Base, UtcDateTime
from all_togetharr.platform.secrets import SecretBox


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime, nullable=False,
        default=lambda: datetime.now(UTC),
    )


class UnknownSettingError(KeyError):
    """Raised for a key not in DEFINITIONS."""


@dataclass(frozen=True)
class SettingDefinition:
    key: str
    value_type: type
    secret: bool = False
    default: Any = None


DEFINITIONS: dict[str, SettingDefinition] = {
    "tmdb.api_key": SettingDefinition("tmdb.api_key", str, secret=True, default=None),
    "tmdb.language": SettingDefinition("tmdb.language", str, secret=False, default="en-US"),
}


class SettingsStore:
    def __init__(self, session: Session, box: SecretBox):
        self._session = session
        self._box = box

    def _def(self, key: str) -> SettingDefinition:
        try:
            return DEFINITIONS[key]
        except KeyError:
            raise UnknownSettingError(key) from None

    def get(self, key: str) -> Any:
        definition = self._def(key)

        row = self._session.get(Setting, key)

        if row is None:
            return definition.default

        value = row.value

        if definition.secret:
            value = self._box.decrypt(value)

        return json.loads(value)

    def set(self, key: str, value: Any) -> None:
        definition = self._def(key)

        if not isinstance(value, definition.value_type):
            raise ValueError(
                f"value must be {definition.value_type.__name__}, "
                f"got {type(value).__name__}"
            )

        encoded = json.dumps(value)

        if definition.secret:
            encoded = self._box.encrypt(encoded)

        now = datetime.now(UTC)

        row = self._session.get(Setting, key)

        if row is None:
            row = Setting(key=key, value=encoded, updated_at=now)
            self._session.add(row)
        else:
            row.value = encoded
            row.updated_at = now

        self._session.flush()

    def delete(self, key: str) -> None:
        self._def(key)

        row = self._session.get(Setting, key)

        if row is not None:
            self._session.delete(row)

        self._session.flush()

    def is_set(self, key: str) -> bool:
        self._def(key)

        row = self._session.get(Setting, key)

        return row is not None
