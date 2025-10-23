from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _auth_headers(email: str = "proj-user@example.com"):
    register_payload = {
        "email": email,
        "password": "Password123",
        "name": "Project Owner",
    }
    register_response = client.post("/api/auth/register", json=register_payload)
    if register_response.status_code not in (200, 400):
        raise AssertionError(f"Unexpected register response: {register_response.status_code}")
    login_response = client.post(
        "/api/auth/login",
        data={"username": register_payload["email"], "password": register_payload["password"]},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_project_accepts_friendly_inputs():
    headers = _auth_headers()
    payload = {
        "name": "AI Sourcing Expansion",
        "status": "On Hold",
        "priority": "High",
        "tags": "ai, sourcing , , automation",
        "team_members": "Alex, Jordan",
    }
    response = client.post("/api/projects", json=payload, headers=headers)
    assert response.status_code == 201
    project = response.json()
    assert project["status"] == "on-hold"
    assert project["priority"] == "high"
    assert project["tags"] == ["ai", "automation", "sourcing"]
    assert project["team_members"] == ["Alex", "Jordan"]
