"""Helpers for working with the local storage directory."""

from __future__ import annotations

from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

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


def _normalize_to_storage_subpath(file_url: str) -> Optional[str]:
    """Return a path relative to the storage directory for a stored file.

    The application frequently stores resume links in a few different formats,
    e.g. "resumes/file.pdf", "storage/resumes/file.pdf" or "/storage/resumes/file.pdf".
    This helper normalises those representations so that we can resolve the
    real filesystem path safely. If the URL points outside of the managed
    storage area (for example an external HTTPS link) ``None`` is returned.
    """

    parsed = urlparse(file_url)
    if parsed.scheme and parsed.scheme not in {"file"}:
        return None

    path = parsed.path if parsed.scheme else file_url
    if not path:
        return None

    path = path.lstrip("/")
    storage_name = Path(settings.storage_path).name
    if path.startswith(f"{storage_name}/"):
        path = path[len(storage_name) + 1 :]
    if not path:
        return None
    return path


def delete_storage_file(file_url: str) -> bool:
    """Delete a file located inside the configured storage directory.

    Returns ``True`` when a file was removed and ``False`` when the path did
    not exist or pointed outside of the managed storage area.
    """

    if not file_url:
        return False

    subpath = _normalize_to_storage_subpath(file_url)
    if not subpath:
        return False

    try:
        resolved = resolve_storage_path(subpath)
    except ValueError:
        return False

    if resolved.is_file():
        resolved.unlink()
        return True
    return False
