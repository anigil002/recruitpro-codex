"""Admin endpoints."""

from datetime import datetime
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import AdminMigrationLog, User
from ..schemas import (
    EmbeddingIndexCreate,
    EmbeddingIndexRead,
    FeatureToggleRead,
    FeatureToggleUpdate,
    PromptPackRead,
)
from ..services.advanced_ai_features import (
    list_embedding_indices,
    list_feature_flags,
    list_prompt_packs,
    register_embedding_index,
    set_feature_flag,
)
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
