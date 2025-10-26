"""Candidate endpoints."""

from datetime import datetime
from typing import Iterable, List, Set, Tuple

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
from ..utils.permissions import can_manage_workspace, ensure_project_access
from ..schemas import (
    CandidateBulkActionRequest,
    CandidateBulkActionResult,
    CandidateCreate,
    CandidatePatch,
    CandidateRead,
    CandidateUpdate,
)
from ..services.activity import log_activity
from ..utils.storage import delete_storage_file
from ..utils.security import generate_id

router = APIRouter(prefix="/api", tags=["candidates"])


def _ensure_candidate_access(candidate: Candidate, current_user, db: Session) -> None:
    """Ensure the current user can manage the given candidate."""

    elevated_roles = {"admin", "super_admin"}

    if candidate.project_id:
        project = ensure_project_access(db.get(Project, candidate.project_id), current_user)
        if project.created_by != current_user.user_id and current_user.role not in elevated_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    elif current_user.role not in elevated_roles.union({"recruiter"}):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


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


def _delete_candidate_record(
    db: Session,
    candidate: Candidate,
    current_user,
    *,
    recalc_metrics: bool = True,
) -> Tuple[Set[str], Set[str]]:
    """Delete a candidate and perform the required cleanup."""

    _ensure_candidate_access(candidate, current_user, db)

    project_ids: Set[str] = set()
    position_ids: Set[str] = set()

    candidate_name = candidate.name
    project_id = candidate.project_id
    position_id = candidate.position_id
    was_hired = candidate.status == "hired"

    if candidate.resume_url:
        delete_storage_file(candidate.resume_url)

    db.delete(candidate)
    log_activity(
        db,
        actor_type="user",
        actor_id=current_user.user_id,
        project_id=project_id,
        position_id=position_id,
        candidate_id=None,
        message=f"Deleted candidate {candidate_name}",
        event_type="candidate_deleted",
    )
    db.flush()

    if was_hired and project_id:
        project_ids.add(project_id)
    if position_id:
        position_ids.add(position_id)

    if recalc_metrics:
        _recalculate_many(db, project_ids, position_ids)

    return project_ids, position_ids


@router.get("/candidates", response_model=List[CandidateRead])
def list_candidates(db: Session = Depends(get_db), current_user=Depends(get_current_user)) -> List[CandidateRead]:
    query = db.query(Candidate).join(Project, isouter=True)
    if not can_manage_workspace(current_user):
        query = query.filter((Project.created_by == current_user.user_id) | (Candidate.project_id.is_(None)))
    candidates = query.all()
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


@router.get("/candidates/duplicates")
def candidate_duplicates(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> List[dict]:
    """Return potential duplicate candidates grouped by matching signals."""

    query = db.query(Candidate).join(Project, isouter=True)
    if not can_manage_workspace(current_user):
        query = query.filter((Project.created_by == current_user.user_id) | (Candidate.project_id.is_(None)))
    candidates = query.all()

    def _serialize(candidate: Candidate) -> dict:
        return {
            "candidate_id": candidate.candidate_id,
            "name": candidate.name,
            "email": candidate.email,
            "status": candidate.status,
            "source": candidate.source,
            "project_id": candidate.project_id,
            "position_id": candidate.position_id,
        }

    groups: list[dict] = []
    for field in ("email", "phone", "resume_url"):
        buckets: dict[str, list[Candidate]] = {}
        for candidate in candidates:
            value = getattr(candidate, field)
            if not value:
                continue
            key = value.strip().lower()
            if not key:
                continue
            buckets.setdefault(key, []).append(candidate)
        for key, items in buckets.items():
            if len(items) < 2:
                continue
            groups.append(
                {
                    "type": field,
                    "value": key,
                    "count": len(items),
                    "candidates": [_serialize(item) for item in items],
                }
            )

    return groups


@router.post("/candidates", response_model=CandidateRead, status_code=status.HTTP_201_CREATED)
def create_candidate(
    payload: CandidateCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> CandidateRead:
    project = None
    if payload.project_id:
        project = ensure_project_access(db.get(Project, payload.project_id), current_user)
    if payload.position_id:
        position = db.get(Position, payload.position_id)
        if not position:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")
        ensure_project_access(db.get(Project, position.project_id), current_user)

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
        ensure_project_access(db.get(Project, candidate.project_id), current_user)
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
        ensure_project_access(db.get(Project, candidate.project_id), current_user)

    updates = payload.dict(exclude_unset=True)
    if "project_id" in updates and updates["project_id"]:
        ensure_project_access(db.get(Project, updates["project_id"]), current_user)
    if "position_id" in updates and updates["position_id"]:
        new_position = db.get(Position, updates["position_id"])
        if not new_position:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")
        ensure_project_access(db.get(Project, new_position.project_id), current_user)

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
        ensure_project_access(db.get(Project, candidate.project_id), current_user)

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
    _delete_candidate_record(db, candidate, current_user)


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
    candidate_map = {candidate.candidate_id: candidate for candidate in candidates}

    action = payload.action.lower()
    if action != "delete" and not candidates:
        return CandidateBulkActionResult(updated=0, deleted=0, message="No candidates matched")
    if action == "add_tag":
        if not payload.tag:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="tag is required for add_tag")
        updated = 0
        for candidate in candidates:
            _ensure_candidate_access(candidate, current_user, db)
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
        success_count = 0
        failed_count = 0
        errors: List[dict] = []
        project_ids: Set[str] = set()
        position_ids: Set[str] = set()

        for candidate_id in payload.candidate_ids:
            candidate = candidate_map.get(candidate_id)
            if not candidate:
                failed_count += 1
                errors.append({"candidate_id": candidate_id, "error": "Candidate not found"})
                continue
            try:
                candidate_project_ids, candidate_position_ids = _delete_candidate_record(
                    db,
                    candidate,
                    current_user,
                    recalc_metrics=False,
                )
            except HTTPException as exc:
                failed_count += 1
                errors.append({"candidate_id": candidate_id, "error": exc.detail})
                continue

            project_ids.update(candidate_project_ids)
            position_ids.update(candidate_position_ids)
            success_count += 1
            candidate_map.pop(candidate_id, None)

        if success_count:
            _recalculate_many(db, project_ids, position_ids)

        message = "Candidates deleted" if success_count else "No candidates deleted"
        return CandidateBulkActionResult(
            deleted=success_count,
            message=message,
            success_count=success_count,
            failed_count=failed_count if failed_count else None,
            errors=errors or None,
        )

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
