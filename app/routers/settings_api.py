"""API endpoints for updating system integration settings."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from sqlalchemy.orm import Session

from ..deps import get_db
from ..services.gemini import gemini
from ..services.integrations import (
    get_integration_value,
    list_integration_status,
    set_integration_credential,
)


router = APIRouter(prefix="/api/settings", tags=["settings"])


class _BaseSettingsPayload(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class GeminiSettingsUpdate(_BaseSettingsPayload):
    """Payload for updating the Gemini API credentials."""

    gemini_api_key: str = Field(..., min_length=4)


class GoogleSettingsUpdate(_BaseSettingsPayload):
    """Payload for updating Google Custom Search credentials."""

    google_api_key: str = Field(..., min_length=4)
    google_cse_id: str = Field(..., min_length=2)


class SmartRecruitersSettingsUpdate(_BaseSettingsPayload):
    """Payload for updating SmartRecruiters credentials."""

    smartrecruiters_email: EmailStr
    smartrecruiters_password: Optional[str] = Field(default=None)
    clear_password: bool = False

    @field_validator("smartrecruiters_password")
    @classmethod
    def _validate_password(cls, value: Optional[str]) -> Optional[str]:
        if value in {None, ""}:
            return value
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        return value


def _success_response(message: str, status_payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"status": "success", "message": message, "integration": status_payload}


@router.post("/gemini")
def update_gemini_settings(
    payload: GeminiSettingsUpdate, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Persist the Gemini API key and return the masked status."""

    try:
        set_integration_credential(
            db, "gemini_api_key", payload.gemini_api_key, user_id="settings_api"
        )
        db.commit()
    except Exception as exc:  # pragma: no cover - defensive guard
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update Gemini settings: {exc}",
        ) from exc

    gemini.configure_api_key(
        get_integration_value("gemini_api_key", session=db) or None
    )

    status_payload = list_integration_status(db).get("gemini_api_key", {})
    return _success_response("Gemini API credentials updated.", status_payload)


@router.post("/google")
def update_google_settings(
    payload: GoogleSettingsUpdate, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Persist Google Custom Search credentials and return the masked status."""

    try:
        set_integration_credential(
            db, "google_api_key", payload.google_api_key, user_id="settings_api"
        )
        set_integration_credential(
            db, "google_cse_id", payload.google_cse_id, user_id="settings_api"
        )
        db.commit()
    except Exception as exc:  # pragma: no cover - defensive guard
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update Google settings: {exc}",
        ) from exc

    status_snapshot = list_integration_status(db)
    status_payload = {
        "google_api_key": status_snapshot.get("google_api_key", {}),
        "google_cse_id": status_snapshot.get("google_cse_id", {}),
    }
    return _success_response(
        "Google Custom Search configuration updated.", status_payload
    )


@router.post("/smartrecruiters")
def update_smartrecruiters_settings(
    payload: SmartRecruitersSettingsUpdate, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Persist SmartRecruiters credentials and return the masked status."""

    try:
        set_integration_credential(
            db, "smartrecruiters_email", payload.smartrecruiters_email, user_id="settings_api"
        )

        if payload.clear_password:
            set_integration_credential(
                db, "smartrecruiters_password", "", user_id="settings_api"
            )
        elif payload.smartrecruiters_password is not None:
            set_integration_credential(
                db,
                "smartrecruiters_password",
                payload.smartrecruiters_password,
                user_id="settings_api",
            )

        db.commit()
    except Exception as exc:  # pragma: no cover - defensive guard
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update SmartRecruiters settings: {exc}",
        ) from exc

    status_snapshot = list_integration_status(db)
    status_payload = {
        "smartrecruiters_email": status_snapshot.get("smartrecruiters_email", {}),
        "smartrecruiters_password": status_snapshot.get(
            "smartrecruiters_password", {}
        ),
    }
    return _success_response(
        "SmartRecruiters credentials updated.", status_payload
    )
