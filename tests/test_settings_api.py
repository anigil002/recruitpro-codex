from fastapi.testclient import TestClient

from app.database import get_session
from app.main import app
from app.services.integrations import get_integration_value


client = TestClient(app)


def test_update_gemini_settings_via_api():
    response = client.post(
        "/api/settings/gemini",
        json={"gemini_api_key": "demo-key-12345"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert "Gemini" in payload["message"]
    assert payload["integration"]["configured"] is True

    with get_session() as session:
        assert (
            get_integration_value("gemini_api_key", session=session)
            == "demo-key-12345"
        )


def test_google_settings_store_and_mask():
    response = client.post(
        "/api/settings/google",
        json={
            "google_api_key": "google-key-987", 
            "google_cse_id": "engine-123", 
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    integration = payload["integration"]
    assert integration["google_api_key"]["configured"] is True
    masked_value = integration["google_api_key"]["masked"]
    assert masked_value and masked_value != "google-key-987"
    assert integration["google_cse_id"]["configured"] is True

    with get_session() as session:
        assert (
            get_integration_value("google_api_key", session=session)
            == "google-key-987"
        )
        assert (
            get_integration_value("google_cse_id", session=session)
            == "engine-123"
        )


def test_smartrecruiters_password_clear_intent():
    # Set the credential with a password
    first_response = client.post(
        "/api/settings/smartrecruiters",
        json={
            "smartrecruiters_email": "ops@example.com",
            "smartrecruiters_password": "SecurePass1",
        },
    )
    assert first_response.status_code == 200

    # Update email without providing a password (should keep existing password)
    second_response = client.post(
        "/api/settings/smartrecruiters",
        json={
            "smartrecruiters_email": "ops@example.com",
            "smartrecruiters_password": None,
        },
    )
    assert second_response.status_code == 200

    with get_session() as session:
        assert (
            get_integration_value("smartrecruiters_password", session=session)
            == "SecurePass1"
        )

    # Explicitly clear the stored password
    clear_response = client.post(
        "/api/settings/smartrecruiters",
        json={
            "smartrecruiters_email": "ops@example.com",
            "smartrecruiters_password": None,
            "clear_password": True,
        },
    )
    assert clear_response.status_code == 200
    clear_payload = clear_response.json()
    assert clear_payload["integration"]["smartrecruiters_password"]["configured"] is False

    with get_session() as session:
        assert (
            get_integration_value("smartrecruiters_password", session=session) == ""
        )
