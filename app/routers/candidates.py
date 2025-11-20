"""Candidate endpoints."""

from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Set, Tuple

import csv
import io

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
try:
    from openpyxl import Workbook
except ImportError:  # pragma: no cover - optional dependency
    Workbook = None
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import Candidate, CandidateStatusHistory, Document, Position, Project, ScreeningRun
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
from ..services.ai import enqueue_cv_screening_job
from ..services.file_upload import validate_and_scan_file
from ..utils.storage import delete_storage_file, ensure_storage_dir
from ..utils.security import generate_id

router = APIRouter(prefix="/api", tags=["candidates"])


def _ensure_candidate_access(candidate: Candidate, current_user, db: Session) -> None:
    """Ensure the current user can manage the given candidate."""

    elevated_roles = {"admin", "super_admin"}

    # Allow access if user created the candidate
    if candidate.created_by == current_user.user_id:
        return

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
        .filter(
            Candidate.project_id == project_id,
            Candidate.status == "hired",
            Candidate.deleted_at.is_(None)  # Exclude soft-deleted
        )
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
    applicants = db.query(Candidate).filter(
        Candidate.position_id == position_id,
        Candidate.deleted_at.is_(None)  # Exclude soft-deleted
    ).count()
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
    # Filter out soft-deleted candidates (STANDARD-DB-005)
    query = query.filter(Candidate.deleted_at.is_(None))
    if not can_manage_workspace(current_user):
        # Users can only see:
        # 1. Candidates in projects they created
        # 2. Candidates they created (regardless of project assignment)
        query = query.filter(
            (Project.created_by == current_user.user_id) |
            (Candidate.created_by == current_user.user_id)
        )
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
            created_by=c.created_by,
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
        created_by=current_user.user_id,
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
        created_by=candidate.created_by,
    )


@router.get("/candidates/{candidate_id}", response_model=CandidateRead)
def get_candidate(candidate_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)) -> CandidateRead:
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    _ensure_candidate_access(candidate, current_user, db)
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
        created_by=candidate.created_by,
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
        created_by=candidate.created_by,
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
        created_by=candidate.created_by,
    )


@router.delete("/candidates/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_candidate(candidate_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)) -> None:
    """Soft delete a candidate per STANDARD-DB-005 (GDPR compliance).

    Sets deleted_at and deleted_by instead of removing the record.
    For hard delete (GDPR right to be forgotten), use the admin endpoint.
    """
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    # Check if already soft-deleted
    if candidate.deleted_at:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    _ensure_candidate_access(candidate, current_user, db)

    # Soft delete
    candidate.deleted_at = datetime.utcnow()
    candidate.deleted_by = current_user.user_id
    db.add(candidate)

    log_activity(
        db,
        actor_type="user",
        actor_id=current_user.user_id,
        project_id=candidate.project_id,
        position_id=candidate.position_id,
        candidate_id=candidate.candidate_id,
        message=f"Soft deleted candidate {candidate.name}",
        event_type="candidate_soft_deleted",
    )

    # Recalculate metrics
    _recalculate_many(db, [candidate.project_id], [candidate.position_id])


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


@router.post("/candidates/upload-cv", status_code=status.HTTP_201_CREATED)
def upload_candidate_cv(
    file: UploadFile = File(...),
    project_id: str | None = Form(None),
    position_id: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Upload a candidate CV and automatically screen it with AI.

    This endpoint:
    1. Uploads the CV file to storage
    2. Creates a Document record
    3. Triggers background CV screening job
    4. AI extracts candidate details (name, email, phone)
    5. AI screens the CV against position requirements
    6. Automatically creates a Candidate record with all details populated

    Returns the job ID for tracking screening progress.
    """

    # Validate project access if project_id is provided
    if project_id:
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        ensure_project_access(project, current_user)

    # Validate position exists if position_id is provided
    if position_id:
        position = db.get(Position, position_id)
        if not position:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")
        # If position has a project, use that project_id
        if position.project_id and not project_id:
            project_id = position.project_id

    # Validate and scan file (STANDARD-SEC-003)
    content, secure_filename = validate_and_scan_file(file)

    # Store the CV file
    storage_dir = ensure_storage_dir()
    file_id = generate_id()
    file_path = storage_dir / f"{file_id}_{secure_filename}"

    # Write with restricted permissions (no execution)
    with file_path.open("wb") as buffer:
        buffer.write(content)
    file_path.chmod(0o644)  # rw-r--r-- (no execute permissions)

    relative_path = file_path.relative_to(storage_dir)

    # Create Document record
    document = Document(
        id=file_id,
        filename=secure_filename,
        mime_type=file.content_type or "application/pdf",
        file_url=str(relative_path),
        scope="candidate_cv",
        scope_id=position_id or project_id,
        owner_user=current_user.user_id,
    )
    db.add(document)

    # Log activity
    log_activity(
        db,
        actor_type="user",
        actor_id=current_user.user_id,
        project_id=project_id,
        message=f"Uploaded CV {secure_filename} for screening (validated and scanned)",
        event_type="cv_uploaded",
    )

    # Enqueue CV screening job
    job = enqueue_cv_screening_job(
        db,
        document_id=file_id,
        project_id=project_id,
        position_id=position_id,
        user_id=current_user.user_id,
    )

    db.commit()

    return {
        "message": "CV uploaded successfully. File validated, scanned, and AI screening has been queued.",
        "document_id": file_id,
        "job_id": job.job_id,
        "filename": secure_filename,
    }


@router.post("/candidates/bulk-upload-cvs", status_code=status.HTTP_201_CREATED)
def bulk_upload_candidate_cvs(
    files: list[UploadFile] = File(...),
    project_id: str | None = Form(None),
    position_id: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Upload multiple candidate CVs and automatically screen them with AI.

    This endpoint:
    1. Uploads multiple CV files to storage
    2. Creates Document records for each file
    3. Triggers background CV screening jobs for each CV
    4. AI extracts candidate details (name, email, phone) for each CV
    5. AI screens each CV against position requirements using the Egis screening criteria
    6. Automatically creates Candidate records with all details populated

    Returns the list of job IDs for tracking screening progress.
    """

    # Validate project access if project_id is provided
    if project_id:
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        ensure_project_access(project, current_user)

    # Validate position exists if position_id is provided
    if position_id:
        position = db.get(Position, position_id)
        if not position:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")
        # If position has a project, use that project_id
        if position.project_id and not project_id:
            project_id = position.project_id

    # Validate file count
    if not files or len(files) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No files provided")

    if len(files) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 50 CVs can be uploaded at once"
        )

    storage_dir = ensure_storage_dir()
    uploaded_files = []
    jobs = []

    # Process each file
    for file in files:
        if not file.filename:
            continue

        try:
            # Validate and scan file (STANDARD-SEC-003)
            content, secure_filename = validate_and_scan_file(file)

            # Store the CV file
            file_id = generate_id()
            file_path = storage_dir / f"{file_id}_{secure_filename}"

            # Write with restricted permissions (no execution)
            with file_path.open("wb") as buffer:
                buffer.write(content)
            file_path.chmod(0o644)  # rw-r--r-- (no execute permissions)

            relative_path = file_path.relative_to(storage_dir)

            # Create Document record
            document = Document(
                id=file_id,
                filename=secure_filename,
                mime_type=file.content_type or "application/pdf",
                file_url=str(relative_path),
                scope="candidate_cv",
                scope_id=position_id or project_id,
                owner_user=current_user.user_id,
            )
            db.add(document)

            # Enqueue CV screening job
            job = enqueue_cv_screening_job(
                db,
                document_id=file_id,
                project_id=project_id,
                position_id=position_id,
                user_id=current_user.user_id,
            )

            uploaded_files.append({
                "filename": secure_filename,
                "document_id": file_id,
                "job_id": job.job_id,
            })
            jobs.append(job.job_id)

        except Exception as e:
            # Log error but continue with other files
            continue

    # Log activity
    log_activity(
        db,
        actor_type="user",
        actor_id=current_user.user_id,
        project_id=project_id,
        message=f"Bulk uploaded {len(uploaded_files)} CVs for screening",
        event_type="bulk_cv_uploaded",
    )

    db.commit()

    return {
        "message": f"Successfully uploaded {len(uploaded_files)} CVs. AI screening has been queued for each CV.",
        "uploaded_count": len(uploaded_files),
        "uploaded_files": uploaded_files,
        "job_ids": jobs,
    }


@router.get("/candidates/{candidate_id}/screening")
def get_candidate_screening_details(
    candidate_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get detailed AI screening results for a candidate.

    Returns the structured screening data including:
    - Table 1: Screening Summary (Overall Fit, Recommended Roles, Key Strengths, Potential Gaps, Notice Period)
    - Table 2: Must-Have Requirement Compliance
    - Final Recommendation and Decision
    """

    # Get the candidate
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    # Ensure access
    _ensure_candidate_access(candidate, current_user, db)

    # Get the most recent screening run for this candidate
    screening_run = (
        db.query(ScreeningRun)
        .filter(ScreeningRun.candidate_id == candidate_id)
        .order_by(ScreeningRun.created_at.desc())
        .first()
    )

    if not screening_run:
        return {
            "candidate_id": candidate_id,
            "has_screening": False,
            "message": "No screening data available for this candidate"
        }

    # Return structured screening data
    return {
        "candidate_id": candidate_id,
        "has_screening": True,
        "screening_id": screening_run.screening_id,
        "position_id": screening_run.position_id,
        "created_at": screening_run.created_at.isoformat() if screening_run.created_at else None,

        # Table 1: Screening Summary
        "table_1_screening_summary": {
            "overall_fit": screening_run.overall_fit,
            "recommended_roles": screening_run.recommended_roles or [],
            "key_strengths": screening_run.key_strengths or [],
            "potential_gaps": screening_run.potential_gaps or [],
            "notice_period": screening_run.notice_period
        },

        # Table 2: Must-Have Requirement Compliance
        "table_2_compliance": screening_run.compliance_table or [],

        # Final Recommendation
        "final_recommendation": {
            "summary": screening_run.final_recommendation,
            "decision": screening_run.final_decision
        },

        # Legacy score_json for backward compatibility
        "score_json": screening_run.score_json or {}
    }
