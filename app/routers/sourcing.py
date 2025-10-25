"""Sourcing orchestration endpoints."""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import AIJob, Position, Project, SourcingJob, SourcingResult
from ..schemas import SmartRecruitersBulkRequest, SourcingJobStatusResponse
from ..services.ai import start_linkedin_xray, start_smartrecruiters_bulk
from ..services.activity import log_activity

router = APIRouter(prefix="/api", tags=["sourcing"])


@router.get("/sourcing/overview")
def sourcing_overview(
    project_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Dict[str, Any]:
    job_query = (
        db.query(SourcingJob)
        .join(Project, SourcingJob.project_id == Project.project_id)
        .filter(Project.created_by == current_user.user_id)
        .order_by(SourcingJob.created_at.desc())
    )
    if project_id:
        job_query = job_query.filter(SourcingJob.project_id == project_id)
    jobs = job_query.all()

    job_payload: list[Dict[str, Any]] = []
    active_jobs = 0
    total_profiles = 0
    tracked_projects: set[str] = set()

    for job in jobs:
        status = (job.status or "pending").lower()
        if status not in {"completed", "failed"}:
            active_jobs += 1
        total_profiles += job.found_count or 0
        if job.project_id:
            tracked_projects.add(job.project_id)

        project = db.get(Project, job.project_id) if job.project_id else None
        position = db.get(Position, job.position_id) if job.position_id else None

        job_payload.append(
            {
                "sourcing_job_id": job.sourcing_job_id,
                "project_name": project.name if project else None,
                "position_title": position.title if position else None,
                "status": job.status,
                "progress": job.progress or 0,
                "found_count": job.found_count or 0,
                "created_at": job.created_at,
                "updated_at": job.updated_at,
            }
        )

    result_query = (
        db.query(SourcingResult)
        .join(SourcingJob, SourcingResult.sourcing_job_id == SourcingJob.sourcing_job_id)
        .join(Project, SourcingJob.project_id == Project.project_id)
        .filter(Project.created_by == current_user.user_id)
        .order_by(SourcingResult.created_at.desc())
    )
    if project_id:
        result_query = result_query.filter(SourcingJob.project_id == project_id)
    results = result_query.limit(12).all()

    result_payload = [
        {
            "result_id": result.result_id,
            "name": result.name,
            "title": result.title,
            "company": result.company,
            "location": result.location,
            "profile_url": result.profile_url,
            "quality_score": result.quality_score,
            "created_at": result.created_at,
        }
        for result in results
    ]

    return {
        "summary": {
            "total_jobs": len(jobs),
            "active_jobs": active_jobs,
            "total_profiles": total_profiles,
            "tracked_projects": len(tracked_projects),
        },
        "jobs": job_payload,
        "results": result_payload,
    }


@router.post("/sourcing/linkedin-xray/start")
def start_linkedin_xray_endpoint(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Dict[str, Any]:
    if "project_id" not in payload:
        raise HTTPException(status_code=400, detail="project_id required")
    job = start_linkedin_xray(db, payload, current_user.user_id)
    log_activity(
        db,
        actor_type="ai",
        actor_id=current_user.user_id,
        project_id=payload.get("project_id"),
        message="LinkedIn X-Ray sourcing started",
        event_type="linkedin_xray_start",
    )
    return {"job_id": job.job_id, "status": job.status}


@router.get("/sourcing/jobs/{job_id}", response_model=SourcingJobStatusResponse)
def sourcing_job_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> SourcingJobStatusResponse:
    job = db.get(SourcingJob, job_id)
    if job:
        results = (
            db.query(SourcingResult)
            .filter(SourcingResult.sourcing_job_id == job.sourcing_job_id)
            .all()
        )
        return SourcingJobStatusResponse(
            job_id=job.sourcing_job_id,
            status=job.status,
            progress=job.progress,
            found_count=job.found_count,
            results=[
                {
                    "platform": result.platform,
                    "profile_url": result.profile_url,
                    "name": result.name,
                    "title": result.title,
                    "location": result.location,
                    "summary": result.summary,
                    "quality_score": result.quality_score,
                }
                for result in results
            ],
        )
    ai_job = db.get(AIJob, job_id)
    if ai_job:
        return SourcingJobStatusResponse(
            job_id=ai_job.job_id,
            status=ai_job.status,
            progress=None,
            found_count=None,
            results=None,
        )
    raise HTTPException(status_code=404, detail="Job not found")


@router.post("/smartrecruiters/bulk")
def smartrecruiters_bulk(
    payload: SmartRecruitersBulkRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Dict[str, Any]:
    job = start_smartrecruiters_bulk(db, payload.model_dump(), current_user.user_id)
    log_activity(
        db,
        actor_type="ai",
        actor_id=current_user.user_id,
        project_id=payload.project_id,
        message="SmartRecruiters bulk automation queued",
        event_type="smartrecruiters",
    )
    return {"job_id": job.job_id, "status": job.status}
