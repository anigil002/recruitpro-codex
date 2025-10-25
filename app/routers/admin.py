"""Admin endpoints."""

from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import AdminMigrationLog, User
from ..schemas import (
    EmbeddingIndexCreate,
    EmbeddingIndexRead,
    FeatureToggleRead,
    FeatureToggleUpdate,
    PromptPackRead,
    UserRoleUpdate,
)
from ..services.activity import log_activity
from ..services.advanced_ai_features import (
    list_embedding_indices,
    list_feature_flags,
    list_prompt_packs,
    register_embedding_index,
    set_feature_flag,
)
from ..services.integrations import list_integration_status
from ..services.migrations import apply_structured_json_migration
from ..utils.security import generate_id

router = APIRouter(prefix="/api", tags=["admin"])


def require_admin(user: User) -> None:
    if user.role not in {"admin", "super_admin"}:
        raise HTTPException(status_code=403, detail="Admin privileges required")


@router.post("/admin/migrate-from-json")
def migrate_from_json(
    payload: Dict[str, object],
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Dict[str, object]:
    require_admin(current_user)

    summary: Optional[Dict[str, object]] = None
    data = payload.get("data")
    if isinstance(data, dict):
        try:
            summary = apply_structured_json_migration(db, data, current_user=current_user)
        except ValueError as error:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    items_total = int(summary["items_total"]) if summary else int(payload.get("items_total", 0) or 0)
    items_success = int(summary["items_success"]) if summary else int(payload.get("items_success", 0) or 0)
    items_failed = int(summary["items_failed"]) if summary else int(payload.get("items_failed", 0) or 0)
    errors = summary.get("errors") if summary else payload.get("errors")

    log = AdminMigrationLog(
        migration_id=generate_id(),
        user_id=current_user.user_id,
        source_name=str(payload.get("source_name", "json")),
        items_total=items_total,
        items_success=items_success,
        items_failed=items_failed,
        error_json=errors,
        created_at=datetime.utcnow(),
    )
    db.add(log)
    db.flush()

    response: Dict[str, object] = {"status": "completed", "migration_id": log.migration_id}
    if summary:
        response["summary"] = summary
    return response


@router.get("/admin/advanced/features", response_model=List[FeatureToggleRead])
def advanced_features(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> List[FeatureToggleRead]:
    require_admin(current_user)
    return [FeatureToggleRead(**item) for item in list_feature_flags(db)]


@router.put("/admin/advanced/features/{key}", response_model=FeatureToggleRead)
def update_feature_toggle(
    key: str,
    payload: FeatureToggleUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> FeatureToggleRead:
    require_admin(current_user)
    record = set_feature_flag(db, key, payload.value, user_id=current_user.user_id)
    db.flush()
    value = record.value_json
    return FeatureToggleRead(
        key=key,
        value=value,
        overridden=True,
        updated_at=record.updated_at,
        updated_by=record.updated_by,
    )


@router.get("/admin/advanced/prompt-packs", response_model=List[PromptPackRead])
def prompt_packs(
    current_user=Depends(get_current_user),
) -> List[PromptPackRead]:
    require_admin(current_user)
    return [PromptPackRead(**pack) for pack in list_prompt_packs()]


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


@router.put("/admin/users/{user_id}/role")
def update_user_role(
    user_id: str,
    payload: UserRoleUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Dict[str, str]:
    require_admin(current_user)
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.role == payload.role:
        return {"status": "unchanged", "user_id": user.user_id, "role": user.role}

    user.role = payload.role
    db.add(user)
    log_activity(
        db,
        actor_type="admin",
        actor_id=current_user.user_id,
        message=f"Updated role for {user.email} to {payload.role}",
        event_type="user_role_updated",
    )
    return {"status": "updated", "user_id": user.user_id, "role": user.role}


@router.get("/admin/integrations")
def admin_integration_status(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Dict[str, Dict[str, object]]:
    require_admin(current_user)
    return list_integration_status(db)


@router.get("/admin/embeddings", response_model=List[EmbeddingIndexRead])
def list_embeddings(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> List[EmbeddingIndexRead]:
    require_admin(current_user)
    return [EmbeddingIndexRead(**item) for item in list_embedding_indices(db)]


@router.post("/admin/embeddings", response_model=EmbeddingIndexRead)
def create_embedding(
    payload: EmbeddingIndexCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> EmbeddingIndexRead:
    require_admin(current_user)
    record = register_embedding_index(db, payload.dict(), user_id=current_user.user_id)
    return EmbeddingIndexRead(
        index_id=record.index_id,
        name=record.name,
        description=record.description,
        vector_dim=record.vector_dim,
        location_uri=record.location_uri,
        created_by=record.created_by,
        created_at=record.created_at,
    )
