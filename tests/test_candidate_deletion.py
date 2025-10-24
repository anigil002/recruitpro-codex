"""Tests covering candidate deletion flows and compliance guarantees."""

from fastapi.testclient import TestClient

from app.database import get_session
from app.main import app
from app.models import ActivityFeed, Candidate, Position, Project
from app.utils.storage import ensure_storage_dir


client = TestClient(app)


def _auth_headers(email: str, *, return_user_id: bool = False, role: str = "recruiter"):
    register_payload = {
        "email": email,
        "password": "Password123",
        "name": "Test User",
        "role": role,
    }
    register_response = client.post("/api/auth/register", json=register_payload)
    if register_response.status_code not in (200, 400):
        raise AssertionError(f"Unexpected register response: {register_response.status_code}")

    user_id = None
    if register_response.status_code == 200:
        user_id = register_response.json()["user_id"]

    login_response = client.post(
        "/api/auth/login",
        data={"username": register_payload["email"], "password": register_payload["password"]},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    if return_user_id and not user_id:
        user_resp = client.get("/api/user", headers=headers)
        if user_resp.status_code == 200:
            user_id = user_resp.json()["user_id"]

    if return_user_id:
        return headers, user_id
    return headers


def _create_project(headers, name="Candidate Ops"):
    response = client.post("/api/projects", json={"name": name}, headers=headers)
    assert response.status_code == 201
    return response.json()["project_id"]


def _create_position(headers, project_id: str, title: str = "Engineer"):
    payload = {
        "project_id": project_id,
        "title": title,
        "status": "open",
    }
    response = client.post("/api/positions", json=payload, headers=headers)
    assert response.status_code == 201
    return response.json()["position_id"]


def test_delete_candidate_removes_resume_and_updates_metrics():
    headers, _ = _auth_headers("candidate-owner@example.com", return_user_id=True)
    project_id = _create_project(headers)
    position_id = _create_position(headers, project_id)

    storage_dir = ensure_storage_dir()
    resume_dir = storage_dir / "resumes"
    resume_dir.mkdir(parents=True, exist_ok=True)
    resume_path = resume_dir / "resume_to_delete.pdf"
    resume_path.write_text("resume bytes", encoding="utf-8")

    candidate_payload = {
        "name": "Candidate To Delete",
        "source": "referral",
        "project_id": project_id,
        "position_id": position_id,
        "status": "hired",
        "resume_url": "/storage/resumes/resume_to_delete.pdf",
    }
    candidate_response = client.post("/api/candidates", json=candidate_payload, headers=headers)
    assert candidate_response.status_code == 201
    candidate_id = candidate_response.json()["candidate_id"]

    with get_session() as session:
        project = session.get(Project, project_id)
        position = session.get(Position, position_id)
        assert project.hires_count == 1
        assert position.applicants_count == 1

    delete_response = client.delete(f"/api/candidates/{candidate_id}", headers=headers)
    assert delete_response.status_code == 204

    assert not resume_path.exists()

    with get_session() as session:
        assert session.get(Candidate, candidate_id) is None
        project = session.get(Project, project_id)
        position = session.get(Position, position_id)
        assert project.hires_count == 0
        assert position.applicants_count == 0
        activity = (
            session.query(ActivityFeed)
            .filter(ActivityFeed.event_type == "candidate_deleted")
            .order_by(ActivityFeed.created_at.desc())
            .first()
        )
        assert activity is not None
        assert activity.candidate_id is None
        assert "Deleted candidate" in activity.message


def test_bulk_delete_reports_missing_and_forbidden_candidates():
    owner_headers, _ = _auth_headers("bulk-owner@example.com", return_user_id=True)
    other_headers, _ = _auth_headers("bulk-other@example.com", return_user_id=True)

    project_id = _create_project(owner_headers, name="Owner Project")
    position_id = _create_position(owner_headers, project_id, title="Owner Role")
    candidate_payload = {
        "name": "Owner Candidate",
        "source": "event",
        "project_id": project_id,
        "position_id": position_id,
    }
    owner_candidate_response = client.post(
        "/api/candidates",
        json=candidate_payload,
        headers=owner_headers,
    )
    assert owner_candidate_response.status_code == 201
    owner_candidate_id = owner_candidate_response.json()["candidate_id"]

    other_project_id = _create_project(other_headers, name="Other Project")
    other_candidate_response = client.post(
        "/api/candidates",
        json={
            "name": "Other Candidate",
            "source": "referral",
            "project_id": other_project_id,
        },
        headers=other_headers,
    )
    assert other_candidate_response.status_code == 201
    other_candidate_id = other_candidate_response.json()["candidate_id"]

    payload = {
        "action": "delete",
        "candidate_ids": [owner_candidate_id, other_candidate_id, "missing-id"],
    }
    response = client.post("/api/candidates/bulk-action", json=payload, headers=owner_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["deleted"] == 1
    assert body["success_count"] == 1
    assert body["failed_count"] == 2
    assert len(body["errors"]) == 2
    errors = {entry["candidate_id"]: entry["error"] for entry in body["errors"]}
    assert errors["missing-id"] == "Candidate not found"
    assert errors[other_candidate_id] == "Insufficient permissions"

    with get_session() as session:
        assert session.get(Candidate, owner_candidate_id) is None
        assert session.get(Candidate, other_candidate_id) is not None
