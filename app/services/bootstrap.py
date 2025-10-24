"""Bootstrap helpers for ensuring critical application data exists."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from ..models import User
from ..utils.security import generate_id, hash_password, verify_password

SUPER_ADMIN_EMAIL = "nigil@na-recruitpro.com"
SUPER_ADMIN_PASSWORD = "nigil123"
SUPER_ADMIN_NAME = "Super Admin"
SUPER_ADMIN_ROLE = "super_admin"


def ensure_super_admin(db: Session) -> None:
    """Create or update the default super admin account.

    The account grants full access to the system and is required for
    administrative bootstrapping when the application is first deployed.
    The password is reset to the configured default if it does not match the
    expected credentials so the operator can always log in.
    """

    user = db.query(User).filter(User.email == SUPER_ADMIN_EMAIL).first()

    if not user:
        db.add(
            User(
                user_id=generate_id(),
                email=SUPER_ADMIN_EMAIL,
                password_hash=hash_password(SUPER_ADMIN_PASSWORD),
                name=SUPER_ADMIN_NAME,
                role=SUPER_ADMIN_ROLE,
                created_at=datetime.utcnow(),
            )
        )
        return

    updated = False

    if user.role != SUPER_ADMIN_ROLE:
        user.role = SUPER_ADMIN_ROLE
        updated = True

    if not user.name:
        user.name = SUPER_ADMIN_NAME
        updated = True

    if not verify_password(SUPER_ADMIN_PASSWORD, user.password_hash):
        user.password_hash = hash_password(SUPER_ADMIN_PASSWORD)
        updated = True

    if updated:
        db.add(user)
