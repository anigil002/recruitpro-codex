"""Reporting and analytics endpoints for the desktop client."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from typing import Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import (
    AIJob,
    ActivityFeed,
    Candidate,
    Interview,
    Position,
    Project,
    ProjectDocument,
    ProjectMarketResearch,
)
from ..utils.permissions import can_manage_workspace

router = APIRouter(prefix="/api", tags=["reporting"])


@router.get("/reporting/overview")
def reporting_overview(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Dict[str, object]:
    """Return a consolidated analytics payload for the renderer."""

    project_query = db.query(Project)
    if not can_manage_workspace(current_user):
        project_query = project_query.filter(Project.created_by == current_user.user_id)
    projects = project_query.all()
    project_counts = Counter((project.status or "unspecified").lower() for project in projects)

    position_query = db.query(Position).join(Project)
    if not can_manage_workspace(current_user):
        position_query = position_query.filter(Project.created_by == current_user.user_id)
    positions = position_query.all()
    position_counts = Counter((position.status or "unspecified").lower() for position in positions)

    candidate_query = db.query(Candidate).join(Project, Project.project_id == Candidate.project_id, isouter=True)
    if not can_manage_workspace(current_user):
        candidate_query = candidate_query.filter(
            (Project.created_by == current_user.user_id) | (Candidate.project_id.is_(None))
        )
    candidates = candidate_query.all()
    candidate_counts = Counter((candidate.status or "unspecified").lower() for candidate in candidates)

    interview_query = db.query(Interview).join(Project)
    if not can_manage_workspace(current_user):
        interview_query = interview_query.filter(Project.created_by == current_user.user_id)
    interviews = interview_query.all()
    now = datetime.utcnow()
    upcoming_interviews = [item for item in interviews if item.scheduled_at and item.scheduled_at >= now]

    document_query = db.query(ProjectDocument).join(Project, Project.project_id == ProjectDocument.project_id, isouter=True)
    if not can_manage_workspace(current_user):
        document_query = document_query.filter(
            (Project.created_by == current_user.user_id) | (ProjectDocument.project_id.is_(None))
        )
    documents_total = document_query.count()

    ai_job_query = db.query(AIJob).join(Project, AIJob.project_id == Project.project_id, isouter=True)
    if not can_manage_workspace(current_user):
        ai_job_query = ai_job_query.filter(
            (AIJob.project_id.is_(None)) | (Project.created_by == current_user.user_id)
        )
    ai_jobs = ai_job_query.order_by(AIJob.created_at.desc()).limit(10).all()
    ai_summary = Counter((job.job_type or "unknown") for job in ai_jobs)

    research_query = db.query(ProjectMarketResearch).join(Project)
    if not can_manage_workspace(current_user):
        research_query = research_query.filter(Project.created_by == current_user.user_id)
    research_rows = (
        research_query
        .order_by(
            ProjectMarketResearch.completed_at.desc().nullslast(),
            ProjectMarketResearch.started_at.desc(),
        )
        .limit(5)
        .all()
    )
    research_payload: List[Dict[str, object]] = []
    for item in research_rows:
        findings = item.findings or []
        if isinstance(findings, dict):
            findings = findings.get("items") or findings.get("data") or []
        research_payload.append(
            {
                "project_id": item.project_id,
                "status": item.status,
                "region": item.region,
                "sector": item.sector,
                "completed_at": item.completed_at or item.started_at,
                "finding_count": len(findings) if isinstance(findings, list) else 0,
            }
        )

    activity_query = db.query(ActivityFeed)
    if not can_manage_workspace(current_user):
        activity_query = activity_query.filter(ActivityFeed.actor_id == current_user.user_id)
    recent_activity = activity_query.order_by(ActivityFeed.created_at.desc()).limit(100).all()
    activity_counter = Counter((item.event_type or "activity").lower() for item in recent_activity)

    window_start = now - timedelta(days=30)
    last_30_days = [item for item in recent_activity if item.created_at and item.created_at >= window_start]
    activity_velocity = Counter((item.event_type or "activity").lower() for item in last_30_days)

    return {
        "projects": {
            "total": len(projects),
            "by_status": project_counts,
        },
        "positions": {
            "total": len(positions),
            "by_status": position_counts,
        },
        "candidates": {
            "total": len(candidates),
            "by_status": candidate_counts,
        },
        "interviews": {
            "total": len(interviews),
            "upcoming": len(upcoming_interviews),
        },
        "documents": {
            "total": documents_total,
        },
        "ai_jobs": {
            "recent": ai_summary,
            "count": len(ai_jobs),
        },
        "market_research": research_payload,
        "activity": {
            "total": len(recent_activity),
            "by_type": activity_counter,
            "velocity_30_days": activity_velocity,
        },
    }
