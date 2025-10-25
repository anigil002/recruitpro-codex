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

router = APIRouter(prefix="/api", tags=["reporting"])


@router.get("/reporting/overview")
def reporting_overview(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Dict[str, object]:
    """Return a consolidated analytics payload for the renderer."""

    project_query = db.query(Project).filter(Project.created_by == current_user.user_id)
    projects = project_query.all()
    project_counts = Counter((project.status or "unspecified").lower() for project in projects)

    position_query = (
        db.query(Position)
        .join(Project)
        .filter(Project.created_by == current_user.user_id)
    )
    positions = position_query.all()
    position_counts = Counter((position.status or "unspecified").lower() for position in positions)

    candidate_query = (
        db.query(Candidate)
        .join(Project, Project.project_id == Candidate.project_id, isouter=True)
        .filter((Project.created_by == current_user.user_id) | (Candidate.project_id.is_(None)))
    )
    candidates = candidate_query.all()
    candidate_counts = Counter((candidate.status or "unspecified").lower() for candidate in candidates)

    interviews = (
        db.query(Interview)
        .join(Project)
        .filter(Project.created_by == current_user.user_id)
        .all()
    )
    now = datetime.utcnow()
    upcoming_interviews = [item for item in interviews if item.scheduled_at and item.scheduled_at >= now]

    documents_total = (
        db.query(ProjectDocument)
        .join(Project, Project.project_id == ProjectDocument.project_id, isouter=True)
        .filter((Project.created_by == current_user.user_id) | (ProjectDocument.project_id.is_(None)))
        .count()
    )

    ai_jobs = (
        db.query(AIJob)
        .join(Project, AIJob.project_id == Project.project_id, isouter=True)
        .filter((AIJob.project_id.is_(None)) | (Project.created_by == current_user.user_id))
        .order_by(AIJob.created_at.desc())
        .limit(10)
        .all()
    )
    ai_summary = Counter((job.job_type or "unknown") for job in ai_jobs)

    research_rows = (
        db.query(ProjectMarketResearch)
        .join(Project)
        .filter(Project.created_by == current_user.user_id)
        .order_by(ProjectMarketResearch.completed_at.desc().nullslast(), ProjectMarketResearch.started_at.desc())
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

    recent_activity = (
        db.query(ActivityFeed)
        .filter(ActivityFeed.actor_id == current_user.user_id)
        .order_by(ActivityFeed.created_at.desc())
        .limit(100)
        .all()
    )
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
