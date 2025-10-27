from app.database import get_session
from app.models import IntegrationCredential, User
from app.services.integrations import (
    get_integration_value,
    list_integration_status,
    set_integration_credential,
)
from app.utils.security import hash_password


def test_integration_credentials_round_trip():
    with get_session() as session:
        user = User(
            user_id="tester",
            email="tester@example.com",
            password_hash=hash_password("password123"),
            name="Test User",
            role="admin",
        )
        session.add(user)
        session.flush()

        set_integration_credential(session, "gemini_api_key", "live-key-123", user_id=user.user_id)
        session.flush()
        record = session.get(IntegrationCredential, "gemini_api_key")
        assert record is not None
        assert record.updated_by == "tester"
        value = get_integration_value("gemini_api_key", session=session)
        assert value == "live-key-123"
        status = list_integration_status(session)["gemini_api_key"]
        assert status["configured"] is True
        assert "123" in status["masked"]


def test_clearing_integration_credential_removes_record():
    with get_session() as session:
        user = User(
            user_id="tester",
            email="tester@example.com",
            password_hash=hash_password("password123"),
            name="Test User",
            role="admin",
        )
        session.add(user)
        session.flush()

        set_integration_credential(session, "google_api_key", "google-key", user_id=user.user_id)
        session.flush()
        set_integration_credential(session, "google_api_key", "", user_id=user.user_id)
        session.flush()
        assert session.get(IntegrationCredential, "google_api_key") is None
        assert get_integration_value("google_api_key", session=session) == ""


def test_integration_credential_without_user_records_as_system():
    with get_session() as session:
        set_integration_credential(session, "google_cse_id", "engine-123", user_id=None)
        session.flush()
        record = session.get(IntegrationCredential, "google_cse_id")
        assert record is not None
        assert record.updated_by is None
        assert get_integration_value("google_cse_id", session=session) == "engine-123"
