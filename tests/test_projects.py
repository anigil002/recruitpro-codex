from fastapi.testclient import TestClient

from unittest.mock import patch

from app.database import get_session
from app.main import app
from app.models import AIJob, Document, Project, ProjectMarketResearch
from app.services.ai import (
    _handle_file_analysis_job,
    _handle_market_research_job,
    create_ai_job,
)
from app.services.gemini import gemini
from app.utils.security import generate_id
from app.utils.storage import ensure_storage_dir


client = TestClient(app)


def _auth_headers(email: str = "proj-user@example.com", *, return_user_id: bool = False):
    register_payload = {
        "email": email,
        "password": "Password123",
        "name": "Project Owner",
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


def test_gemini_generates_job_descriptions_for_title_list(tmp_path):
    file_path = tmp_path / "titles.txt"
    file_path.write_text("Project Manager\nSite Engineer\n")

    analysis = gemini.analyze_file(
        file_path,
        original_name="titles.txt",
        mime_type="text/plain",
        project_context={"summary": "Mega project delivery"},
    )

    assert analysis["document_type"] == "job_titles"
    assert analysis["job_descriptions_generated"] is True
    assert len(analysis["positions"]) == 2
    for position in analysis["positions"]:
        assert position["description"]
        assert position["responsibilities"]
        assert position["requirements"]


def test_scope_document_triggers_market_research_job(tmp_path):
    headers, user_id = _auth_headers(return_user_id=True)
    project_response = client.post("/api/projects", json={"name": "Metro Expansion"}, headers=headers)
    assert project_response.status_code == 201
    project_id = project_response.json()["project_id"]

    storage_dir = ensure_storage_dir()
    file_id = generate_id()
    stored_name = f"{file_id}_scope.txt"
    file_path = storage_dir / stored_name
    file_path.write_text(
        "Project Scope of Work\nClient: Egis Infrastructure\n"
        "Scope of Work covers design, supervision, and commissioning for a five-year rail programme."
    )

    with get_session() as session:
        document = Document(
            id=file_id,
            filename="scope.txt",
            file_url=stored_name,
            mime_type="text/plain",
            owner_user=user_id,
            scope="project",
            scope_id=project_id,
        )
        session.add(document)

    with get_session() as session:
        job = create_ai_job(
            session,
            "file_analysis",
            project_id=project_id,
            request={"document_id": file_id, "user_id": user_id},
        )
        session.flush()
        job_id = job.job_id

    with patch("app.services.ai.background_queue.enqueue") as enqueue_mock, patch(
        "app.services.ai.events.publish_sync"
    ):
        _handle_file_analysis_job({"job_id": job_id})
        enqueue_mock.assert_called()

    with get_session() as session:
        research_job = (
            session.query(AIJob)
            .filter(AIJob.project_id == project_id, AIJob.job_type == "market_research")
            .order_by(AIJob.created_at.desc())
            .first()
        )
        assert research_job is not None
        research_job_id = research_job.job_id

    _handle_market_research_job({"job_id": research_job_id})

    with get_session() as session:
        project = session.get(Project, project_id)
        assert project.research_done == 1
        record = (
            session.query(ProjectMarketResearch)
            .filter(ProjectMarketResearch.project_id == project_id)
            .one()
        )
        assert record.status == "completed"
        assert record.findings
