"""Utilities for consistent API error responses."""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping

from fastapi import status


_ERROR_HINTS: dict[int, str] = {
    status.HTTP_400_BAD_REQUEST: "Double-check the information you provided and try again.",
    status.HTTP_401_UNAUTHORIZED: "Verify your credentials or request access from an administrator.",
    status.HTTP_403_FORBIDDEN: "You do not have permission to perform this action.",
    status.HTTP_404_NOT_FOUND: "Confirm the resource still exists or refresh and try again.",
    status.HTTP_409_CONFLICT: "Resolve the conflict and submit the request once more.",
    status.HTTP_422_UNPROCESSABLE_ENTITY: "Review the highlighted fields for validation errors.",
    status.HTTP_429_TOO_MANY_REQUESTS: "You have reached the rate limit. Wait a moment and try again.",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "Something went wrong on our side. Please try again shortly.",
}


def _stringify_detail(detail: Any) -> str:
    """Return a human-friendly string for the detail payload."""

    if detail is None:
        return "An unexpected error occurred."
    if isinstance(detail, str):
        return detail
    if isinstance(detail, Mapping):
        message = detail.get("message") or detail.get("detail")
        if isinstance(message, str):
            return message
    if isinstance(detail, (list, tuple)):
        parts: list[str] = []
        for item in detail:
            if isinstance(item, Mapping):
                msg = item.get("msg") or item.get("message") or item.get("detail")
                if isinstance(msg, str):
                    parts.append(msg)
                    continue
            if isinstance(item, str):
                parts.append(item)
        if parts:
            return "; ".join(parts)
    return str(detail)


def build_error_response(
    detail: Any,
    status_code: int,
    *,
    code: str | None = None,
    errors: list[MutableMapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create a structured error payload with a helpful hint when available."""

    message = _stringify_detail(detail)
    hint = _ERROR_HINTS.get(status_code)
    error_payload: dict[str, Any] = {
        "code": code or f"http_{status_code}",
        "message": message,
    }
    if hint:
        error_payload["hint"] = hint
    if errors:
        error_payload["details"] = errors
    return {
        "detail": message,
        "error": error_payload,
    }

