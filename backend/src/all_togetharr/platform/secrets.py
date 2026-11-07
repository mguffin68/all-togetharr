"""Fernet-based encryption for secret settings."""

import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

KEY_FILENAME = "secret.key"


class SecretDecryptError(Exception):
    """Raised when a secret cannot be decrypted."""


def load_or_create_key(config_dir: Path) -> bytes:
    """Create or load the Fernet key file with strict permissions."""
    path = config_dir / KEY_FILENAME
    config_dir.mkdir(parents=True, exist_ok=True)

    if not path.exists():
        key = Fernet.generate_key()
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            pass
        else:
            try:
                os.write(fd, key)
            finally:
                os.close(fd)
            return key

    # Tighten permissions if too loose
    current_mode = os.stat(path).st_mode & 0o777
    if current_mode != 0o600:
        os.chmod(path, 0o600)

    key = path.read_bytes()

    try:
        Fernet(key)
    except Exception as exc:
        raise ValueError(
            f"{path} is not a valid Fernet key: {exc}"
        ) from exc

    return key


class SecretBox:
    """Encrypt and decrypt values using Fernet."""

    def __init__(self, key: bytes):
        self._fernet = Fernet(key)

    def encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.encode()).decode()

    def decrypt(self, token: str) -> str:
        try:
            return self._fernet.decrypt(token.encode()).decode()
        except (InvalidToken, ValueError, TypeError):
            raise SecretDecryptError("cannot decrypt this value") from None
