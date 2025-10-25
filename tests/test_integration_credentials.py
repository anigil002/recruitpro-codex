from app.database import get_session
from app.models import IntegrationCredential
from app.services.integrations import (
    get_integration_value,
    list_integration_status,
    set_integration_credential,
)


def test_integration_credentials_round_trip():
    with get_session() as session:
        set_integration_credential(session, "gemini_api_key", "live-key-123", user_id="tester")
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
        set_integration_credential(session, "google_api_key", "google-key", user_id="tester")
        session.flush()
        set_integration_credential(session, "google_api_key", "", user_id="tester")
        session.flush()
        assert session.get(IntegrationCredential, "google_api_key") is None
        assert get_integration_value("google_api_key", session=session) == ""
