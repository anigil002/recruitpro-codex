from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from ..models import ActivityFeed
from ..utils.security import generate_id
from .realtime import events


def log_activity(
    session: Session,
    *,
    actor_type: str,
    message: str,
    event_type: str,
    actor_id: Optional[str] = None,
    project_id: Optional[str] = None,
    position_id: Optional[str] = None,
    candidate_id: Optional[str] = None,
) -> ActivityFeed:
    activity = ActivityFeed(
        activity_id=generate_id(),
        actor_type=actor_type,
        actor_id=actor_id,
        project_id=project_id,
        position_id=position_id,
        candidate_id=candidate_id,
        event_type=event_type,
        message=message,
        created_at=datetime.utcnow(),
    )
    session.add(activity)
    events.publish_sync(
        {
            "type": "activity",
            "user_id": actor_id,
            "payload": {
                "message": message,
                "event_type": event_type,
                "project_id": project_id,
                "position_id": position_id,
                "candidate_id": candidate_id,
                "created_at": activity.created_at.isoformat(),
            },
        }
    )
    return activity
