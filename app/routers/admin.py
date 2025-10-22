"""Admin endpoints."""

from datetime import datetime
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import AdminMigrationLog, AdvancedFeaturesConfig, EmbeddingIndexRef, User
from ..utils.security import generate_id

router = APIRouter(prefix="/api", tags=["admin"])


def require_admin(user: User) -> None:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")


@router.post("/admin/migrate-from-json")
def migrate_from_json(
    payload: Dict[str, int],
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Dict[str, str]:
    require_admin(current_user)
    log = AdminMigrationLog(
        migration_id=generate_id(),
        user_id=current_user.user_id,
        source_name=payload.get("source_name", "json"),
        items_total=payload.get("items_total", 0),
        items_success=payload.get("items_success", 0),
        items_failed=payload.get("items_failed", 0),
        error_json=payload.get("errors"),
        created_at=datetime.utcnow(),
    )
    db.add(log)
    return {"status": "completed", "migration_id": log.migration_id}


@router.post("/admin/database/optimize")
def database_optimize(
    payload: Dict[str, str] | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Dict[str, str]:
    require_admin(current_user)
    return {"status": "optimized"}


@router.get("/admin/users")
def list_users(db: Session = Depends(get_db), current_user=Depends(get_current_user)) -> Dict[str, list]:
    require_admin(current_user)
    users = db.query(User).all()
    return {
        "users": [
            {
                "user_id": user.user_id,
                "email": user.email,
                "name": user.name,
                "role": user.role,
            }
            for user in users
        ]
    }
