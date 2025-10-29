"""Helpers for managing integration credentials persisted in the database."""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Dict, Optional

from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_session
from ..models import IntegrationCredential, User
from ..utils.secrets import decrypt_secret, encrypt_secret, mask_secret


IntegrationStatus = Dict[str, object]

ENV_FALLBACKS: Dict[str, Callable[[object], str]] = {
    "gemini_api_key": lambda settings: settings.gemini_api_key_value,
    "google_api_key": lambda settings: settings.google_search_api_key_value,
    "google_cse_id": lambda settings: settings.google_custom_search_engine_id or "",
    "smartrecruiters_email": lambda settings: settings.smartrecruiters_email or "",
    "smartrecruiters_password": lambda settings: settings.smartrecruiters_password_value,
}

TRACKED_KEYS = set(ENV_FALLBACKS.keys())


def _normalise_key(key: str) -> str:
    value = (key or "").strip().lower()
    if value not in TRACKED_KEYS:
        raise KeyError(f"Unknown integration credential '{key}'")
    return value


def _load_record(session: Session, key: str) -> Optional[IntegrationCredential]:
    return session.get(IntegrationCredential, key)


def _resolve_user_id(session: Session, user_id: Optional[str]) -> Optional[str]:
    """Return the ID if it belongs to a persisted user, otherwise ``None``."""

    if not user_id:
        return None

    # ``session.get`` will hit the identity map first, so the lookup is cheap when
    # the caller already has the user loaded in the active transaction.
    user = session.get(User, user_id)
    return user.user_id if user else None


def set_integration_credential(
    session: Session, key: str, value: Optional[str], *, user_id: Optional[str]
) -> None:
    """Persist or remove a credential value."""

    normalized = _normalise_key(key)
    record = _load_record(session, normalized)
    actor_id = _resolve_user_id(session, user_id)

    if not value:
        if record:
            session.delete(record)
            session.flush()
        return

    encrypted = encrypt_secret(value)
    now = datetime.utcnow()
    if record:
        record.value_encrypted = encrypted
        record.updated_at = now
        record.updated_by = actor_id
        session.add(record)
    else:
        session.add(
            IntegrationCredential(
                key=normalized,
                value_encrypted=encrypted,
                updated_by=actor_id,
                updated_at=now,
            )
        )

    session.flush()


def get_integration_value(key: str, *, session: Optional[Session] = None) -> str:
    """Return the decrypted credential value or fall back to environment config."""

    normalized = _normalise_key(key)

    def _lookup(db: Session) -> str:
        record = _load_record(db, normalized)
        if not record:
            return ""
        try:
            return decrypt_secret(record.value_encrypted)
        except ValueError:
            return ""

    if session is not None:
        value = _lookup(session)
    else:
        with get_session() as db:
            value = _lookup(db)

    if value:
        return value

    settings = get_settings()
    fallback = ENV_FALLBACKS.get(normalized)
    return fallback(settings) if fallback else ""


def list_integration_status(session: Session) -> Dict[str, IntegrationStatus]:
    """Return UI friendly credential information without exposing secrets."""

    settings = get_settings()
    status: Dict[str, IntegrationStatus] = {}

    for key in sorted(TRACKED_KEYS):
        record = _load_record(session, key)
        source = None
        plain_value = ""
        if record:
            try:
                plain_value = decrypt_secret(record.value_encrypted)
                source = "database"
            except ValueError:
                plain_value = ""
        if not plain_value:
            fallback = ENV_FALLBACKS.get(key)
            if fallback:
                env_value = fallback(settings)
                if env_value:
                    plain_value = env_value
                    source = "environment"

        status[key] = {
            "configured": bool(plain_value),
            "masked": mask_secret(plain_value),
            "updated_at": record.updated_at if record else None,
            "updated_by": record.updated_by if record else None,
            "source": source,
        }

    return status
