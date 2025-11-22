"""Security helpers for password hashing and JWT tokens."""

import re
from datetime import datetime, timedelta
from hashlib import sha256
from typing import List, Optional
from uuid import uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext

from ..config import get_settings

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
settings = get_settings()


class PasswordValidationError(ValueError):
    """Raised when password doesn't meet complexity requirements."""

    pass


def validate_password_strength(password: str) -> None:
    """Validate password meets security requirements.

    Requirements (OWASP-compliant):
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)
    - No common weak passwords

    Raises:
        PasswordValidationError: If password doesn't meet requirements
    """
    errors: List[str] = []

    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")

    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter")

    if not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter")

    if not re.search(r"\d", password):
        errors.append("Password must contain at least one digit")

    if not re.search(r"[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]", password):
        errors.append("Password must contain at least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)")

    # Check against common weak passwords
    weak_passwords = {
        "password", "password1", "password123", "12345678", "qwerty123",
        "abc123", "letmein", "welcome", "admin123", "changeme",
        "p@ssw0rd", "p@ssword", "passw0rd"
    }
    if password.lower() in weak_passwords:
        errors.append("Password is too common. Please choose a stronger password")

    # Check for sequential characters
    if re.search(r"(012|123|234|345|456|567|678|789|890|abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)", password.lower()):
        errors.append("Password contains sequential characters. Please choose a more complex password")

    if errors:
        raise PasswordValidationError("; ".join(errors))


def _normalize_password(password: str) -> str:
    encoded = password.encode("utf-8")
    if len(encoded) <= 72:
        return password
    return sha256(encoded).hexdigest()


def hash_password(password: str) -> str:
    return pwd_context.hash(_normalize_password(password))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(_normalize_password(plain_password), hashed_password)


def create_access_token(subject: str, expires_minutes: Optional[int] = None) -> str:
    expire_minutes = expires_minutes or settings.access_token_expire_minutes
    expire = datetime.utcnow() + timedelta(minutes=expire_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.secret_key_value, algorithm=settings.algorithm)


def decode_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, settings.secret_key_value, algorithms=[settings.algorithm])
    except JWTError:
        return None
    return payload.get("sub")


def generate_id() -> str:
    return uuid4().hex
