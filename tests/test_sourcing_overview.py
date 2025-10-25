from datetime import datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from app.database import get_session
from app.main import app
from app.models import Position, Project, SourcingJob, SourcingResult
from app.utils.security import generate_id

client = TestClient(app)


def _auth_headers(*, return_user_id: bool = False):
    email = f"sourcing-{uuid4().hex}@example.com"
    payload = {
        "email": email,
        "password": "Sup3rSecure!",
        "name": "Sourcing Analyst",
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


def test_sourcing_overview_requires_authentication():
    response = client.get("/api/sourcing/overview")
    assert response.status_code == 401


def test_sourcing_overview_includes_summary_metrics():
    headers, user_id = _auth_headers(return_user_id=True)

    project_id = generate_id()
    position_id = generate_id()
    job_id = generate_id()
    result_id = generate_id()

    with get_session() as session:
        session.add(
            Project(
                project_id=project_id,
                name="LaunchPad Expansion",
                created_by=user_id,
                created_at=datetime.utcnow(),
            )
        )
        session.add(
            Position(
                position_id=position_id,
                project_id=project_id,
                title="Growth Lead",
                department="Marketing",
                status="active",
                created_at=datetime.utcnow(),
            )
        )
        session.add(
            SourcingJob(
                sourcing_job_id=job_id,
                project_id=project_id,
                position_id=position_id,
                params_json={"keywords": ["growth", "b2b"]},
                status="running",
                progress=35,
                found_count=12,
                created_at=datetime.utcnow(),
            )
        )
        session.add(
            SourcingResult(
                result_id=result_id,
                sourcing_job_id=job_id,
                platform="LinkedIn",
                profile_url="https://example.com/profile",
                name="Alex Rivera",
                title="Growth Manager",
                company="Acme",
                location="Remote",
                quality_score=82,
                created_at=datetime.utcnow(),
            )
        )

    response = client.get("/api/sourcing/overview", headers=headers)
    assert response.status_code == 200
    payload = response.json()

    assert payload["summary"]["total_jobs"] == 1
    assert payload["summary"]["active_jobs"] == 1
    assert payload["summary"]["total_profiles"] == 12
    assert payload["summary"]["tracked_projects"] == 1

    assert payload["jobs"], "Expected the overview to include job metadata"
    job = payload["jobs"][0]
    assert job["project_name"] == "LaunchPad Expansion"
    assert job["position_title"] == "Growth Lead"
    assert job["status"] == "running"
    assert job["found_count"] == 12

    assert payload["results"], "Expected recent sourcing results to be included"
    result = payload["results"][0]
    assert result["name"] == "Alex Rivera"
    assert result["title"] == "Growth Manager"
