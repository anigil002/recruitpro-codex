from uuid import uuid4

from fastapi.testclient import TestClient

from app.database import get_session
from app.main import app
from app.models import ActivityFeed
from app.utils.security import generate_id

client = TestClient(app)


def _auth_headers(*, return_user_id: bool = False):
    email = f"activity-{uuid4().hex}@example.com"
    payload = {
        "email": email,
        "password": "Str0ngPass!",
        "name": "Activity User",
    }
    register_response = client.post("/api/auth/register", json=payload)
    assert register_response.status_code == 200
    user_id = register_response.json()["user_id"]

    login_response = client.post(
        "/api/auth/login",
        data={"username": email, "password": payload["password"]},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    if return_user_id:
        return headers, user_id
    return headers


def test_activity_requires_authentication():
    response = client.get("/api/activity")
    assert response.status_code == 401


def test_dashboard_requires_authentication():
    response = client.get("/api/dashboard/stats")
    assert response.status_code == 401


def test_activity_returns_only_current_user_events():
    headers, user_id = _auth_headers(return_user_id=True)

    with get_session() as session:
        session.add(
            ActivityFeed(
                activity_id=generate_id(),
                actor_type="user",
                actor_id=user_id,
                project_id=None,
                position_id=None,
                candidate_id=None,
                event_type="custom",
                message="Only for current user",
            )
        )
        session.add(
            ActivityFeed(
                activity_id=generate_id(),
                actor_type="user",
                actor_id="other-user",
                project_id=None,
                position_id=None,
                candidate_id=None,
                event_type="custom",
                message="Should not leak",
            )
        )

    response = client.get("/api/activity", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload, "Expected at least one activity event for the current user"
    assert all(item["actor_id"] == user_id for item in payload)
    assert all(item["message"] != "Should not leak" for item in payload)


def test_dashboard_stats_empty_account():
    headers, _ = _auth_headers(return_user_id=True)
    response = client.get("/api/dashboard/stats", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["projects"] == 0
    assert data["candidates"] == 0
    assert data["pipeline"]["total"] == 0
