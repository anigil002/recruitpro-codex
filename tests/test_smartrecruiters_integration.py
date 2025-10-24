import pytest
from pydantic import SecretStr
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_session
from app.models import AIJob, Candidate, Position, Project, User
from app.services.ai import create_ai_job, _handle_smartrecruiters
from app.services.smartrecruiters import SmartRecruitersCandidate, SmartRecruitersJob
from app.utils.security import generate_id


class DummySmartRecruitersClient:
    def __init__(self, *args, **kwargs):
        self._jobs = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def fetch_candidates(self, job: SmartRecruitersJob):
        self._jobs.append(job)
        return [
            SmartRecruitersCandidate(
                name="Alice Example",
                email="alice@example.com",
                status="Interview",
                stage="Interview",
                profile_url="https://smartrecruiters.example/candidate/alice",
                tags=["pipeline"],
            ),
            SmartRecruitersCandidate(
                name="Bob Example",
                email="bob@example.com",
                status="Hired",
                stage="Hired",
                resume_url="https://smartrecruiters.example/resume/bob.pdf",
            ),
        ]


@pytest.fixture(autouse=True)
def _configure_settings(monkeypatch):
    settings = get_settings()
    settings.smartrecruiters_email = "bot@example.com"
    settings.smartrecruiters_password = SecretStr("password123")
    settings.smartrecruiters_base_url = "https://smartrecruiters.example"
    monkeypatch.setattr("app.services.smartrecruiters.SmartRecruitersClient", DummySmartRecruitersClient)
    yield
    settings.smartrecruiters_email = None
    settings.smartrecruiters_password = None
    settings.smartrecruiters_base_url = "https://app.smartrecruiters.com"


def _create_project_with_position(session: Session, *, user_id: str) -> tuple[Project, Position]:
    project = Project(
        project_id=generate_id(),
        name="SR Project",
        status="active",
        priority="medium",
        created_by=user_id,
    )
    position = Position(
        position_id=generate_id(),
        project_id=project.project_id,
        title="Integration Engineer",
        status="open",
    )
    session.add_all([project, position])
    return project, position


def _create_user(session: Session) -> User:
    user = User(
        user_id=generate_id(),
        email="sr-owner@example.com",
        password_hash="hashed",
        name="SR Owner",
        role="recruiter",
    )
    session.add(user)
    return user


def test_smartrecruiters_handler_imports_candidates(monkeypatch):
    settings = get_settings()
    with get_session() as session:
        user = _create_user(session)
        project, position = _create_project_with_position(session, user_id=user.user_id)
        job = create_ai_job(
            session,
            "smartrecruiters_bulk",
            project_id=project.project_id,
            request={
                "project_id": project.project_id,
                "jobs": [
                    {
                        "position_id": position.position_id,
                        "job_url": "https://smartrecruiters.example/jobs/123",
                    }
                ],
                "user_id": user.user_id,
                "notes": "priority intake",
            },
        )
        session.flush()
        job_id = job.job_id

    _handle_smartrecruiters({"job_id": job_id})

    with get_session() as session:
        job = session.get(AIJob, job_id)
        assert job.status == "completed"
        summary = job.response_json
        assert summary["imported"] == 2
        candidates = session.query(Candidate).filter(Candidate.project_id == summary["project_id"]).all()
        assert len(candidates) == 2
        emails = {candidate.email for candidate in candidates}
        assert emails == {"alice@example.com", "bob@example.com"}
        tags = {tuple(candidate.tags or []) for candidate in candidates}
        assert any("smartrecruiters" in tag_tuple for tag_tuple in tags)
        position = session.get(Position, position.position_id)
        assert position.applicants_count == 2
        project = session.get(Project, project.project_id)
        assert project.hires_count == 1


def test_smartrecruiters_handler_updates_existing_candidates(monkeypatch):
    with get_session() as session:
        user = _create_user(session)
        project, position = _create_project_with_position(session, user_id=user.user_id)
        candidate = Candidate(
            candidate_id=generate_id(),
            project_id=project.project_id,
            position_id=position.position_id,
            name="Alice Example",
            email="alice@example.com",
            source="smartrecruiters",
            status="new",
        )
        session.add(candidate)
        job = create_ai_job(
            session,
            "smartrecruiters_bulk",
            project_id=project.project_id,
            request={
                "project_id": project.project_id,
                "jobs": [
                    {
                        "position_id": position.position_id,
                        "job_url": "https://smartrecruiters.example/jobs/456",
                    }
                ],
                "user_id": user.user_id,
            },
        )
        session.flush()
        job_id = job.job_id

    _handle_smartrecruiters({"job_id": job_id})

    with get_session() as session:
        job = session.get(AIJob, job_id)
        assert job.status == "completed"
        summary = job.response_json
        assert summary["updated"] == 1
        refreshed = session.get(Candidate, candidate.candidate_id)
        assert refreshed.status == "interview"
        assert "smartrecruiters" in (refreshed.tags or [])
