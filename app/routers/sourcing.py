"""Sourcing-related endpoints."""

from typing import Dict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..services.ai import enqueue_ai_job

router = APIRouter(prefix="/api", tags=["sourcing"])


@router.post("/sourcing/linkedin-xray/start")
def start_linkedin_xray(
    payload: Dict[str, str],
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Dict[str, str]:
    job = enqueue_ai_job(db, "linkedin_xray", request=payload, response={"status": "started"})
    return {"job_id": job.job_id, "status": "started"}


@router.get("/sourcing/jobs/{job_id}")
def sourcing_job_status(job_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)) -> Dict[str, str]:
    from ..models import AIJob

    job = db.get(AIJob, job_id)
    if not job:
        return {"status": "unknown"}
    return {"status": job.status, "job_id": job.job_id}


@router.post("/smartrecruiters/bulk")
def smartrecruiters_bulk(
    payload: Dict[str, str],
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Dict[str, str]:
    job = enqueue_ai_job(db, "smartrecruiters_bulk", request=payload, response={"status": "queued"})
    return {"job_id": job.job_id, "status": "queued"}
