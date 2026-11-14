"""Symmetric encryption for OAuth tokens and other secrets at rest.

Uses Fernet (AES-128-CBC + HMAC) with a key supplied via APP_ENCRYPTION_KEY.
The key is managed separately from the database. If no key is configured,
encryption fails loudly rather than silently storing plaintext secrets.
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings


class EncryptionError(RuntimeError):
    """Raised when encryption/decryption cannot be performed."""


def _get_fernet() -> Fernet:
    settings = get_settings()
    key = settings.app_encryption_key
    if not key:
        raise EncryptionError(
            "APP_ENCRYPTION_KEY is not set. Generate one with:\n"
            '  python -c "from cryptography.fernet import Fernet; '
            'print(Fernet.generate_key().decode())"'
        )
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except (ValueError, TypeError) as exc:  # pragma: no cover - config error
        raise EncryptionError(f"Invalid APP_ENCRYPTION_KEY: {exc}") from exc


def encrypt(plaintext: str) -> str:
    """Encrypt a string, returning a URL-safe base64 token."""
    if plaintext is None:
        return ""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt(token: str) -> str:
    """Decrypt a token produced by :func:`encrypt`."""
    if not token:
        return ""
    try:
        return _get_fernet().decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise EncryptionError("Could not decrypt value (wrong key or corrupt data).") from exc


def generate_key() -> str:
    """Generate a fresh Fernet key (helper for setup)."""
    return Fernet.generate_key().decode()
