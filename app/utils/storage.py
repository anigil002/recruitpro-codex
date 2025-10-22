"""Helpers for working with the local storage directory."""

from __future__ import annotations

from pathlib import Path

from ..config import get_settings

settings = get_settings()


def resolve_storage_path(file_path: str) -> Path:
    base = Path(settings.storage_path).resolve()
    candidate = Path(file_path)
    if not candidate.is_absolute():
        candidate = base / candidate
    try:
        resolved = candidate.resolve(strict=False)
    except FileNotFoundError:
        resolved = base / candidate
    if resolved == base:
        return resolved
    try:
        resolved.relative_to(base)
    except ValueError as exc:
        raise ValueError("File path escapes storage directory") from exc
    return resolved


def ensure_storage_dir() -> Path:
    base = Path(settings.storage_path).resolve()
    base.mkdir(parents=True, exist_ok=True)
    return base
