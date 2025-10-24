from __future__ import annotations

from fastapi.testclient import TestClient

from app.database import get_session
from app.main import app
from app.models import AIJob, Candidate, ChatbotSession, Position
from app.utils.security import generate_id


client = TestClient(app)


def _auth_headers(email: str, *, return_user_id: bool = False):
    payload = {"email": email, "password": "Password123", "name": "Chat Bot"}
    register = client.post("/api/auth/register", json=payload)
    if register.status_code not in (200, 400):
        raise AssertionError(f"Unexpected register response: {register.status_code}")
    user_id = None
    if register.status_code == 200:
        user_id = register.json()["user_id"]
    login = client.post(
        "/api/auth/login",
        data={"username": payload["email"], "password": payload["password"]},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    if return_user_id and not user_id:
        me = client.get("/api/user", headers=headers)
        if me.status_code == 200:
            user_id = me.json()["user_id"]
    if return_user_id:
        return headers, user_id
    return headers


def test_chatbot_tracks_context_and_projects():
    headers, user_id = _auth_headers("chatbot-user@example.com", return_user_id=True)

    project_response = client.post("/api/projects", json={"name": "Riyadh Metro"}, headers=headers)
    assert project_response.status_code == 201
    project = project_response.json()
    project_id = project["project_id"]

    with get_session() as session:
        position = Position(
            position_id=generate_id(),
            project_id=project_id,
            title="Senior Project Manager",
            status="open",
            responsibilities=["Lead delivery"],
            requirements=["PMP", "Rail"],
        )
        session.add(position)
        session.add(
            Candidate(
                candidate_id=generate_id(),
                project_id=project_id,
                position_id=position.position_id,
                name="Sara Pipeline",
                source="referral",
                status="interview",
            )
        )
        session.add(
            Candidate(
                candidate_id=generate_id(),
                project_id=project_id,
                position_id=position.position_id,
                name="Tom Screening",
                source="sourcing",
                status="screening",
            )
        )

    focus = client.post(
        "/api/chatbot",
        json={"message": "Let's focus on the Riyadh Metro project."},
        headers=headers,
    )
    assert focus.status_code == 200
    session_id = focus.json()["session_id"]

    status = client.post(
        "/api/chatbot",
        json={"session_id": session_id, "message": "What's the status right now?"},
        headers=headers,
    )
    assert status.status_code == 200
    payload = status.json()

    assert "Riyadh Metro" in payload["reply"]
    assert "Pipeline" in payload["reply"]
    assert "market_research" in ",".join(payload["tools_suggested"])
    assert payload["context_echo"]

    with get_session() as session:
        stored = session.get(ChatbotSession, session_id)
        assert stored is not None
        assert stored.context_json.get("project_focus", {}).get("project_id") == project_id


def test_chatbot_launches_market_research_job():
    headers, user_id = _auth_headers("chatbot-market@example.com", return_user_id=True)
    project_response = client.post("/api/projects", json={"name": "Quantum Hub"}, headers=headers)
    assert project_response.status_code == 201
    project_id = project_response.json()["project_id"]

    response = client.post(
        "/api/chatbot",
        json={"message": "Please run market research for the Quantum Hub project."},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()

    assert "Job" in data["reply"]
    assert any(tool.startswith("market_research") for tool in data["tools_suggested"])

    with get_session() as session:
        jobs = (
            session.query(AIJob)
            .filter(AIJob.project_id == project_id, AIJob.job_type == "market_research")
            .all()
        )
        assert jobs, "Market research job should be queued"
        stored_session = session.get(ChatbotSession, data["session_id"])
        pending = stored_session.context_json.get("pending_jobs", []) if stored_session else []
        assert any(job.get("job_type") == "market_research" for job in pending)
