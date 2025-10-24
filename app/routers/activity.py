"""Activity and dashboard endpoints."""

import asyncio
import json
from typing import AsyncGenerator, List, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import ActivityFeed, Candidate, Project
from ..schemas import ActivityRead
from ..services.realtime import events

router = APIRouter(prefix="/api", tags=["activity"])


@router.get("/activity", response_model=List[ActivityRead])
def list_activity(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> List[ActivityRead]:
    items = (
        db.query(ActivityFeed)
        .filter(ActivityFeed.actor_id == current_user.user_id)
        .order_by(ActivityFeed.created_at.desc())
        .limit(100)
        .all()
    )
    return [
        ActivityRead(
            activity_id=item.activity_id,
            actor_type=item.actor_type,
            actor_id=item.actor_id,
            project_id=item.project_id,
            position_id=item.position_id,
            candidate_id=item.candidate_id,
            event_type=item.event_type,
            message=item.message,
            created_at=item.created_at,
        )
        for item in items
]


@router.get("/dashboard/stats")
def dashboard_stats(db: Session = Depends(get_db), current_user=Depends(get_current_user)) -> dict:
    projects_count = db.query(Project).filter(Project.created_by == current_user.user_id).count()
    candidate_query = (
        db.query(Candidate)
        .join(Project, isouter=True)
        .filter(or_(Project.created_by == current_user.user_id, Candidate.project_id.is_(None)))
    )
    candidates_count = candidate_query.count()

    pipeline_counts = {
        "total": candidates_count,
        "sourcing": 0,
        "screening": 0,
        "interviews": 0,
        "offers": 0,
    }
    for status, count in (
        candidate_query.with_entities(Candidate.status, func.count(Candidate.candidate_id)).group_by(Candidate.status).all()
    ):
        key = status.lower() if status else ""
        if "source" in key:
            pipeline_counts["sourcing"] += count
        elif "screen" in key:
            pipeline_counts["screening"] += count
        elif "interview" in key:
            pipeline_counts["interviews"] += count
        elif "offer" in key:
            pipeline_counts["offers"] += count

    featured_candidate = (
        candidate_query.order_by(desc(func.coalesce(Candidate.rating, 0)), Candidate.created_at.desc()).first()
    )
    featured_payload: Optional[dict] = None
    if featured_candidate:
        featured_payload = {
            "name": featured_candidate.name,
            "summary": (
                f"{featured_candidate.status.title()} · {featured_candidate.rating or 'unrated'}"
                if featured_candidate.status
                else "Pipeline candidate"
            ),
            "tags": sorted(set(featured_candidate.tags or []))[:4],
        }

    suggestions = []
    if pipeline_counts["sourcing"] == 0:
        suggestions.append("No sourcing activity yet. Upload a project brief to start automation.")
    if pipeline_counts["screening"] == 0:
        suggestions.append("Run AI screening to qualify your new applicants automatically.")
    if not featured_payload:
        suggestions.append("Add candidates to see spotlight insights here.")

    return {
        "projects": projects_count,
        "candidates": candidates_count,
        "pipeline": pipeline_counts,
        "featured_candidate": featured_payload,
        "suggestions": suggestions,
    }


@router.get("/activity/stream")
async def activity_stream(
    current_user=Depends(get_current_user),
) -> StreamingResponse:
    async def event_generator() -> AsyncGenerator[str, None]:
        async for event in events.subscribe(user_id=current_user.user_id):
            payload = json.dumps(event.get("payload", {}))
            event_type = event.get("type", "activity")
            yield f"event: {event_type}\ndata: {payload}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
