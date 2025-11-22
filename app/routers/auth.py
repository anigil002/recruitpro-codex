"""Authentication routes."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..deps import get_db, get_current_user
from ..models import User
from ..schemas import (
    ChangePasswordRequest,
    Token,
    UserCreate,
    UserRead,
    UserSettingsUpdate,
    UserUpdate,
)
from ..services.activity import log_activity
from ..utils.security import (
    PasswordValidationError,
    create_access_token,
    generate_id,
    hash_password,
    validate_password_strength,
    verify_password,
)

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/auth/register", response_model=UserRead)
def register_user(payload: UserCreate, db: Session = Depends(get_db)) -> UserRead:
    if db.query(User).filter(User.email == payload.email.lower()).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    # Validate password strength (STANDARD-SEC-001)
    try:
        validate_password_strength(payload.password)
    except PasswordValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    user = User(
        user_id=generate_id(),
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        name=payload.name,
        role=payload.role,
        created_at=datetime.utcnow(),
    )
    db.add(user)
    log_activity(
        db,
        actor_type="system",
        actor_id=user.user_id,
        message=f"User {user.email} registered",
        event_type="user_registered",
    )
    db.flush()
    return UserRead(
        user_id=user.user_id,
        email=user.email,
        name=user.name,
        role=user.role,
        created_at=user.created_at,
        settings=user.settings,
    )


@router.post("/auth/login", response_model=Token)
def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    user = db.query(User).filter(User.email == form_data.username.lower()).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    token = create_access_token(user.user_id)
    log_activity(
        db,
        actor_type="user",
        actor_id=user.user_id,
        message="User logged in",
        event_type="login",
    )
    return Token(access_token=token)


@router.post("/auth/logout")
def logout_user(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    log_activity(
        db,
        actor_type="user",
        actor_id=current_user.user_id,
        message="User logged out",
        event_type="logout",
    )
    return {"status": "ok"}


@router.post("/auth/change-password")
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect password")

    # Validate new password strength (STANDARD-SEC-001)
    try:
        validate_password_strength(payload.new_password)
    except PasswordValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    current_user.password_hash = hash_password(payload.new_password)
    db.add(current_user)
    log_activity(
        db,
        actor_type="user",
        actor_id=current_user.user_id,
        message="Password changed",
        event_type="password_change",
    )
    return {"status": "updated"}


@router.get("/user", response_model=UserRead)
def get_user(current_user: User = Depends(get_current_user)) -> UserRead:
    return UserRead(
        user_id=current_user.user_id,
        email=current_user.email,
        name=current_user.name,
        role=current_user.role,
        created_at=current_user.created_at,
        settings=current_user.settings,
    )


@router.put("/user/profile", response_model=UserRead)
def update_profile(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserRead:
    if payload.name:
        current_user.name = payload.name
    db.add(current_user)
    return UserRead(
        user_id=current_user.user_id,
        email=current_user.email,
        name=current_user.name,
        role=current_user.role,
        created_at=current_user.created_at,
        settings=current_user.settings,
    )


@router.put("/user/settings", response_model=UserRead)
def update_settings(
    payload: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserRead:
    current_user.settings = payload.settings
    db.add(current_user)
    return UserRead(
        user_id=current_user.user_id,
        email=current_user.email,
        name=current_user.name,
        role=current_user.role,
        created_at=current_user.created_at,
        settings=current_user.settings,
    )
