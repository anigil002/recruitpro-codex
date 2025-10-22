"""Candidate endpoints."""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import Candidate, CandidateStatusHistory, Position, Project
from ..schemas import CandidateCreate, CandidatePatch, CandidateRead, CandidateUpdate
from ..services.activity import log_activity
from ..utils.security import generate_id

router = APIRouter(prefix="/api", tags=["candidates"])


@router.get("/candidates", response_model=List[CandidateRead])
def list_candidates(db: Session = Depends(get_db), current_user=Depends(get_current_user)) -> List[CandidateRead]:
    candidates = (
        db.query(Candidate)
        .join(Project, isouter=True)
        .filter((Project.created_by == current_user.user_id) | (Candidate.project_id.is_(None)))
        .all()
    )
    return [
        CandidateRead(
            candidate_id=c.candidate_id,
            project_id=c.project_id,
            position_id=c.position_id,
            name=c.name,
            email=c.email,
            phone=c.phone,
            source=c.source,
            status=c.status,
            rating=c.rating,
            resume_url=c.resume_url,
            ai_score=c.ai_score,
            created_at=c.created_at,
        )
        for c in candidates
    ]


@router.post("/candidates", response_model=CandidateRead, status_code=status.HTTP_201_CREATED)
def create_candidate(
    payload: CandidateCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> CandidateRead:
    if payload.project_id:
        project = db.get(Project, payload.project_id)
        if not project or project.created_by != current_user.user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if payload.position_id:
        position = db.get(Position, payload.position_id)
        if not position:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")

    candidate = Candidate(
        candidate_id=generate_id(),
        project_id=payload.project_id,
        position_id=payload.position_id,
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        source=payload.source,
        status=payload.status or "new",
        rating=payload.rating,
        resume_url=payload.resume_url,
        created_at=datetime.utcnow(),
    )
    db.add(candidate)
    log_activity(
        db,
        actor_type="user",
        actor_id=current_user.user_id,
        project_id=candidate.project_id,
        position_id=candidate.position_id,
        candidate_id=candidate.candidate_id,
        message=f"Created candidate {candidate.name}",
        event_type="candidate_created",
    )
    db.flush()
    return CandidateRead(
        candidate_id=candidate.candidate_id,
        project_id=candidate.project_id,
        position_id=candidate.position_id,
        name=candidate.name,
        email=candidate.email,
        phone=candidate.phone,
        source=candidate.source,
        status=candidate.status,
        rating=candidate.rating,
        resume_url=candidate.resume_url,
        ai_score=candidate.ai_score,
        created_at=candidate.created_at,
    )


@router.get("/candidates/{candidate_id}", response_model=CandidateRead)
def get_candidate(candidate_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)) -> CandidateRead:
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    if candidate.project_id:
        project = db.get(Project, candidate.project_id)
        if not project or project.created_by != current_user.user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    return CandidateRead(
        candidate_id=candidate.candidate_id,
        project_id=candidate.project_id,
        position_id=candidate.position_id,
        name=candidate.name,
        email=candidate.email,
        phone=candidate.phone,
        source=candidate.source,
        status=candidate.status,
        rating=candidate.rating,
        resume_url=candidate.resume_url,
        ai_score=candidate.ai_score,
        created_at=candidate.created_at,
    )


@router.put("/candidates/{candidate_id}", response_model=CandidateRead)
def update_candidate(
    candidate_id: str,
    payload: CandidateUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> CandidateRead:
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    if candidate.project_id:
        project = db.get(Project, candidate.project_id)
        if not project or project.created_by != current_user.user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    for field, value in payload.dict(exclude_unset=True).items():
        setattr(candidate, field, value)
    db.add(candidate)
    return CandidateRead(
        candidate_id=candidate.candidate_id,
        project_id=candidate.project_id,
        position_id=candidate.position_id,
        name=candidate.name,
        email=candidate.email,
        phone=candidate.phone,
        source=candidate.source,
        status=candidate.status,
        rating=candidate.rating,
        resume_url=candidate.resume_url,
        ai_score=candidate.ai_score,
        created_at=candidate.created_at,
    )


@router.patch("/candidates/{candidate_id}", response_model=CandidateRead)
def patch_candidate(
    candidate_id: str,
    payload: CandidatePatch,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> CandidateRead:
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    previous_status = candidate.status
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(candidate, field, value)
    db.add(candidate)

    if payload.status and payload.status != previous_status:
        history = CandidateStatusHistory(
            history_id=generate_id(),
            candidate_id=candidate.candidate_id,
            old_status=previous_status,
            new_status=candidate.status,
            changed_by=current_user.user_id,
            changed_at=datetime.utcnow(),
        )
        db.add(history)
        log_activity(
            db,
            actor_type="user",
            actor_id=current_user.user_id,
            project_id=candidate.project_id,
            position_id=candidate.position_id,
            candidate_id=candidate.candidate_id,
            message=f"Candidate {candidate.name} status changed to {candidate.status}",
            event_type="candidate_status_changed",
        )

    return CandidateRead(
        candidate_id=candidate.candidate_id,
        project_id=candidate.project_id,
        position_id=candidate.position_id,
        name=candidate.name,
        email=candidate.email,
        phone=candidate.phone,
        source=candidate.source,
        status=candidate.status,
        rating=candidate.rating,
        resume_url=candidate.resume_url,
        ai_score=candidate.ai_score,
        created_at=candidate.created_at,
    )


@router.delete("/candidates/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_candidate(candidate_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)) -> None:
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    if candidate.project_id:
        project = db.get(Project, candidate.project_id)
        if not project or project.created_by != current_user.user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    db.delete(candidate)
    log_activity(
        db,
        actor_type="user",
        actor_id=current_user.user_id,
        project_id=candidate.project_id,
        position_id=candidate.position_id,
        candidate_id=candidate.candidate_id,
        message=f"Deleted candidate {candidate.name}",
        event_type="candidate_deleted",
    )
