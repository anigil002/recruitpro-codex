from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"


def test_version_endpoint():
    response = client.get("/api/version")
    assert response.status_code == 200
    payload = response.json()
    assert payload["app"] == "RecruitPro"


def test_register_and_login_flow():
    register_payload = {
        "email": "admin@example.com",
        "password": "Password123",
        "name": "Admin",
        "role": "admin",
    }
    response = client.post("/api/auth/register", json=register_payload)
    assert response.status_code == 200
    login_response = client.post(
        "/api/auth/login",
        data={"username": register_payload["email"], "password": register_payload["password"]},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    me_response = client.get("/api/user", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == 200
    assert me_response.json()["email"] == register_payload["email"]


def test_super_admin_role_round_trip():
    login_response = client.post(
        "/api/auth/login",
        data={"username": "nigil@na-recruitpro.com", "password": "nigil123"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    me_response = client.get("/api/user", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == 200
    payload = me_response.json()
    assert payload["email"] == "nigil@na-recruitpro.com"
    assert payload["role"] == "super_admin"
