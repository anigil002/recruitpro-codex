"""Activity and dashboard endpoints."""

import json
from typing import AsyncGenerator, List

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import ActivityFeed, Candidate, Project
from ..schemas import ActivityRead
from ..services.realtime import events

router = APIRouter(prefix="/api", tags=["activity"])


@router.get("/activity", response_model=List[ActivityRead])
def list_activity(db: Session = Depends(get_db), current_user=Depends(get_current_user)) -> List[ActivityRead]:
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
    candidates_count = (
        db.query(Candidate)
        .join(Project, isouter=True)
        .filter((Project.created_by == current_user.user_id) | (Candidate.project_id.is_(None)))
        .count()
    )
    return {
        "projects": projects_count,
        "candidates": candidates_count,
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
