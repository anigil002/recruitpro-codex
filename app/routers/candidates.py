"""Candidate endpoints."""

from datetime import datetime
from typing import Iterable, List, Set

import csv
import io

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
try:
    from openpyxl import Workbook
except ImportError:  # pragma: no cover - optional dependency
    Workbook = None
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import Candidate, CandidateStatusHistory, Position, Project
from ..schemas import (
    CandidateBulkActionRequest,
    CandidateBulkActionResult,
    CandidateCreate,
    CandidatePatch,
    CandidateRead,
    CandidateUpdate,
)
from ..services.activity import log_activity
from ..utils.security import generate_id

router = APIRouter(prefix="/api", tags=["candidates"])


def _recalculate_project_hires(db: Session, project_id: str | None) -> None:
    if not project_id:
        return
    project = db.get(Project, project_id)
    if not project:
        return
    hires = (
        db.query(Candidate)
        .filter(Candidate.project_id == project_id, Candidate.status == "hired")
        .count()
    )
    project.hires_count = hires
    db.add(project)


def _recalculate_position_applicants(db: Session, position_id: str | None) -> None:
    if not position_id:
        return
    position = db.get(Position, position_id)
    if not position:
        return
    applicants = db.query(Candidate).filter(Candidate.position_id == position_id).count()
    position.applicants_count = applicants
    db.add(position)


def _recalculate_many(
    db: Session,
    project_ids: Iterable[str | None],
    position_ids: Iterable[str | None],
) -> None:
    seen_projects: Set[str] = {pid for pid in project_ids if pid}
    seen_positions: Set[str] = {pid for pid in position_ids if pid}
    for project_id in seen_projects:
        _recalculate_project_hires(db, project_id)
    for position_id in seen_positions:
        _recalculate_position_applicants(db, position_id)


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
            tags=c.tags,
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
        tags=sorted(set(payload.tags or [])) if payload.tags is not None else None,
        created_at=datetime.utcnow(),
    )
    db.add(candidate)
    db.flush()
    _recalculate_many(db, [candidate.project_id], [candidate.position_id])
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
        tags=candidate.tags,
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
        tags=candidate.tags,
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

    updates = payload.dict(exclude_unset=True)
    if "project_id" in updates and updates["project_id"]:
        new_project = db.get(Project, updates["project_id"])
        if not new_project or new_project.created_by != current_user.user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if "position_id" in updates and updates["position_id"]:
        new_position = db.get(Position, updates["position_id"])
        if not new_position:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")

    previous_project_id = candidate.project_id
    previous_position_id = candidate.position_id
    previous_status = candidate.status

    for field, value in updates.items():
        if field == "tags" and value is not None:
            value = sorted(set(value))
        setattr(candidate, field, value)
    db.add(candidate)
    db.flush()
    _recalculate_many(
        db,
        [previous_project_id, candidate.project_id] if previous_status != candidate.status or previous_project_id != candidate.project_id else [candidate.project_id],
        [previous_position_id, candidate.position_id] if previous_position_id != candidate.position_id else [candidate.position_id],
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
        tags=candidate.tags,
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
    if candidate.project_id:
        project = db.get(Project, candidate.project_id)
        if not project or project.created_by != current_user.user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    previous_status = candidate.status
    for field, value in payload.dict(exclude_unset=True).items():
        if field == "tags" and value is not None:
            value = sorted(set(value))
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

    db.flush()
    if payload.status and payload.status != previous_status:
        _recalculate_many(db, [candidate.project_id], [candidate.position_id])

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
        tags=candidate.tags,
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
    previous_project_id = candidate.project_id if candidate.status == "hired" else None
    previous_position_id = candidate.position_id
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
    db.flush()
    _recalculate_many(db, [previous_project_id] if previous_project_id else [], [previous_position_id] if previous_position_id else [])


@router.post("/candidates/bulk-action")
def candidates_bulk_action(
    payload: CandidateBulkActionRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not payload.candidate_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="candidate_ids required")

    candidates = (
        db.query(Candidate)
        .filter(Candidate.candidate_id.in_(payload.candidate_ids))
        .all()
    )
    if not candidates:
        return CandidateBulkActionResult(updated=0, deleted=0, message="No candidates matched")

    for candidate in candidates:
        if candidate.project_id:
            project = db.get(Project, candidate.project_id)
            if not project or project.created_by != current_user.user_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Candidate outside your projects")

    action = payload.action.lower()
    if action == "add_tag":
        if not payload.tag:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="tag is required for add_tag")
        updated = 0
        for candidate in candidates:
            tags = set(candidate.tags or [])
            if payload.tag not in tags:
                tags.add(payload.tag)
                candidate.tags = sorted(tags)
                updated += 1
            db.add(candidate)
        log_activity(
            db,
            actor_type="user",
            actor_id=current_user.user_id,
            message=f"Applied tag '{payload.tag}' to {updated} candidates",
            event_type="candidate_bulk_tag",
        )
        return CandidateBulkActionResult(updated=updated, message="Tag applied")

    if action == "delete":
        deleted = 0
        project_ids: Set[str] = set()
        position_ids: Set[str] = set()
        for candidate in candidates:
            if candidate.status == "hired" and candidate.project_id:
                project_ids.add(candidate.project_id)
            if candidate.position_id:
                position_ids.add(candidate.position_id)
            db.delete(candidate)
            deleted += 1
        log_activity(
            db,
            actor_type="user",
            actor_id=current_user.user_id,
            message=f"Bulk deleted {deleted} candidates",
            event_type="candidate_bulk_delete",
        )
        db.flush()
        _recalculate_many(db, project_ids, position_ids)
        return CandidateBulkActionResult(deleted=deleted, message="Candidates deleted")

    if action == "export":
        headers = ["Candidate ID", "Name", "Email", "Phone", "Status", "Source", "Tags"]
        rows = [
            [
                candidate.candidate_id,
                candidate.name,
                candidate.email or "",
                candidate.phone or "",
                candidate.status,
                candidate.source,
                ", ".join(candidate.tags or []),
            ]
            for candidate in candidates
        ]
        log_activity(
            db,
            actor_type="user",
            actor_id=current_user.user_id,
            message=f"Exported {len(rows)} candidates ({payload.export_format})",
            event_type="candidate_bulk_export",
        )
        if payload.export_format == "xlsx":
            if Workbook is None:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="xlsx export requires openpyxl",
                )
            workbook = Workbook()
            sheet = workbook.active
            sheet.append(headers)
            for row in rows:
                sheet.append(row)
            output = io.BytesIO()
            workbook.save(output)
            output.seek(0)
            return StreamingResponse(
                output,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": "attachment; filename=candidates.xlsx"},
            )

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        writer.writerows(rows)
        content = output.getvalue().encode("utf-8")
        return StreamingResponse(
            iter([content]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=candidates.csv"},
        )

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported action")
