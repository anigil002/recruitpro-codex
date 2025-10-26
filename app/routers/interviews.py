"""Interview endpoints."""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import Candidate, Interview, Position, Project
from ..services.activity import log_activity
from ..utils.permissions import can_manage_workspace, ensure_project_access
from ..utils.security import generate_id

router = APIRouter(prefix="/api", tags=["interviews"])


@router.get("/interviews")
def list_interviews(db: Session = Depends(get_db), current_user=Depends(get_current_user)) -> List[dict]:
    query = db.query(Interview).join(Position).join(Project)
    if not can_manage_workspace(current_user):
        query = query.filter(Project.created_by == current_user.user_id)
    interviews = query.all()
    return [
        {
            "interview_id": interview.interview_id,
            "candidate_id": interview.candidate_id,
            "position_id": interview.position_id,
            "project_id": interview.project_id,
            "scheduled_at": interview.scheduled_at,
            "location": interview.location,
            "mode": interview.mode,
            "notes": interview.notes,
            "feedback": interview.feedback,
        }
        for interview in interviews
    ]


@router.post("/interviews", status_code=status.HTTP_201_CREATED)
def schedule_interview(
    payload: dict,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    candidate = db.get(Candidate, payload.get("candidate_id"))
    position = db.get(Position, payload.get("position_id"))
    if not candidate or not position:
        raise HTTPException(status_code=404, detail="Candidate or position not found")
    if candidate.project_id:
        ensure_project_access(db.get(Project, candidate.project_id), current_user)
    ensure_project_access(db.get(Project, position.project_id), current_user)

    interview = Interview(
        interview_id=generate_id(),
        project_id=candidate.project_id,
        position_id=position.position_id,
        candidate_id=candidate.candidate_id,
        scheduled_at=datetime.fromisoformat(payload["scheduled_at"]),
        location=payload.get("location"),
        mode=payload.get("mode"),
        notes=payload.get("notes"),
        created_at=datetime.utcnow(),
    )
    db.add(interview)
    log_activity(
        db,
        actor_type="user",
        actor_id=current_user.user_id,
        project_id=candidate.project_id,
        position_id=position.position_id,
        candidate_id=candidate.candidate_id,
        message="Interview scheduled",
        event_type="interview_scheduled",
    )
    return {"interview_id": interview.interview_id}


@router.put("/interviews/{interview_id}")
def update_interview(
    interview_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> dict:
    interview = db.get(Interview, interview_id)
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    ensure_project_access(db.get(Project, interview.project_id), current_user)

    for field in ["scheduled_at", "location", "mode", "notes", "feedback"]:
        if field in payload:
            value = payload[field]
            if field == "scheduled_at" and value:
                value = datetime.fromisoformat(value)
            setattr(interview, field, value)
    interview.updated_at = datetime.utcnow()
    interview.updated_by = current_user.user_id
    db.add(interview)
    return {"status": "updated"}
