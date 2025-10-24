"""Sourcing orchestration endpoints."""

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import AIJob, SourcingJob, SourcingResult
from ..schemas import SmartRecruitersBulkRequest, SourcingJobStatusResponse
from ..services.ai import start_linkedin_xray, start_smartrecruiters_bulk
from ..services.activity import log_activity

router = APIRouter(prefix="/api", tags=["sourcing"])


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
