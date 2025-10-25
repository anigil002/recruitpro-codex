"""Helpers for encrypting and decrypting sensitive configuration values."""

from __future__ import annotations

import base64
import binascii
from hashlib import sha256
from typing import Optional

from ..config import get_settings


def _derive_key() -> bytes:
    settings = get_settings()
    return sha256(settings.secret_key_value.encode("utf-8")).digest()


def _xor_bytes(data: bytes, key: bytes) -> bytes:
    if not key:
        raise ValueError("Encryption key cannot be empty")
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def encrypt_secret(value: str) -> str:
    """Encrypt a plaintext value for storage in the database."""

    if value is None:
        raise ValueError("Secret value cannot be None")
    key = _derive_key()
    encrypted = _xor_bytes(value.encode("utf-8"), key)
    return base64.urlsafe_b64encode(encrypted).decode("utf-8")


def decrypt_secret(token: str) -> str:
    """Decrypt a stored secret value."""

    if not token:
        return ""
    key = _derive_key()
    try:
        encrypted = base64.urlsafe_b64decode(token.encode("utf-8"))
    except (ValueError, binascii.Error) as exc:  # type: ignore[name-defined]
        raise ValueError("Stored secret is not valid base64 data") from exc
    data = _xor_bytes(encrypted, key)
    return data.decode("utf-8")


def mask_secret(value: Optional[str]) -> str:
    """Return a masked representation suitable for UI display."""

    if not value:
        return ""
    length = len(value)
    if length <= 4:
        return "●" * length
    visible = value[-4:]
    return "●" * (length - 4) + visible
