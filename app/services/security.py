"""
Security Services

This module provides security-related functionality including:
- ClamAV virus scanning
- Password history tracking
- Password strength validation
- Security audit logging
"""

import hashlib
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import get_settings

settings = get_settings()


def scan_file_with_clamav(file_path: str) -> Dict[str, any]:
    """
    Scan a file for viruses using ClamAV.

    Args:
        file_path: Path to file to scan

    Returns:
        Dict with scan results:
        {
            'clean': bool,
            'threats': List[str],
            'scan_time': float,
            'error': Optional[str]
        }

    Raises:
        FileNotFoundError: If file doesn't exist
        RuntimeError: If ClamAV is not installed
    """
    file_path_obj = Path(file_path)

    if not file_path_obj.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    start_time = datetime.utcnow()

    try:
        # Run clamdscan (faster, uses clamd daemon)
        # Falls back to clamscan if clamdscan not available
        try:
            result = subprocess.run(
                ["clamdscan", "--no-summary", str(file_path)],
                capture_output=True,
                text=True,
                timeout=60,
            )
            scanner = "clamdscan"
        except FileNotFoundError:
            result = subprocess.run(
                ["clamscan", "--no-summary", str(file_path)],
                capture_output=True,
                text=True,
                timeout=120,
            )
            scanner = "clamscan"

        scan_time = (datetime.utcnow() - start_time).total_seconds()

        # Parse output
        # Return code 0 = clean
        # Return code 1 = infected
        # Return code 2 = error
        if result.returncode == 0:
            return {
                "clean": True,
                "threats": [],
                "scan_time": scan_time,
                "scanner": scanner,
            }
        elif result.returncode == 1:
            # Extract threat names from output
            threats = []
            for line in result.stdout.split("\n"):
                if "FOUND" in line:
                    # Extract threat name
                    parts = line.split(":")
                    if len(parts) >= 2:
                        threat = parts[-2].strip()
                        threats.append(threat)

            return {
                "clean": False,
                "threats": threats,
                "scan_time": scan_time,
                "scanner": scanner,
            }
        else:
            return {
                "clean": False,
                "threats": [],
                "scan_time": scan_time,
                "scanner": scanner,
                "error": f"Scanner error: {result.stderr}",
            }

    except FileNotFoundError:
        raise RuntimeError(
            "ClamAV not installed. Install with: sudo apt-get install clamav clamav-daemon"
        )
    except subprocess.TimeoutExpired:
        scan_time = (datetime.utcnow() - start_time).total_seconds()
        return {
            "clean": False,
            "threats": [],
            "scan_time": scan_time,
            "error": "Scan timeout (file too large or scanner unresponsive)",
        }
    except Exception as e:
        scan_time = (datetime.utcnow() - start_time).total_seconds()
        return {
            "clean": False,
            "threats": [],
            "scan_time": scan_time,
            "error": str(e),
        }


def check_password_history(
    user_id: str,
    new_password: str,
    session: Session,
) -> bool:
    """
    Check if a password has been used before by this user.

    Args:
        user_id: User ID
        new_password: New password to check
        session: Database session

    Returns:
        bool: True if password is acceptable (not in history), False if already used
    """
    if settings.password_history_count == 0:
        return True

    # Hash the new password
    new_password_hash = hashlib.sha256(new_password.encode()).hexdigest()

    # Get user's password history
    result = session.execute(
        text(
            """
            SELECT password_hash
            FROM password_history
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            LIMIT :limit
            """
        ),
        {"user_id": user_id, "limit": settings.password_history_count}
    )

    history = [row[0] for row in result]

    # Check if new password hash is in history
    return new_password_hash not in history


def store_password_in_history(
    user_id: str,
    password_hash: str,
    session: Session,
) -> None:
    """
    Store a password hash in the user's password history.

    Args:
        user_id: User ID
        password_hash: Hashed password to store
        session: Database session
    """
    # Create password_history table if it doesn't exist
    session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS password_history (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR NOT NULL,
                password_hash VARCHAR NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
            """
        )
    )

    # Hash the password hash for additional security
    secure_hash = hashlib.sha256(password_hash.encode()).hexdigest()

    # Insert new password
    session.execute(
        text(
            """
            INSERT INTO password_history (user_id, password_hash, created_at)
            VALUES (:user_id, :password_hash, :created_at)
            """
        ),
        {
            "user_id": user_id,
            "password_hash": secure_hash,
            "created_at": datetime.utcnow(),
        }
    )

    # Clean up old history entries
    session.execute(
        text(
            """
            DELETE FROM password_history
            WHERE user_id = :user_id
            AND id NOT IN (
                SELECT id FROM password_history
                WHERE user_id = :user_id
                ORDER BY created_at DESC
                LIMIT :limit
            )
            """
        ),
        {"user_id": user_id, "limit": settings.password_history_count}
    )


def validate_password_strength(password: str) -> Dict[str, any]:
    """
    Validate password strength.

    Requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character

    Args:
        password: Password to validate

    Returns:
        Dict with validation results:
        {
            'valid': bool,
            'errors': List[str],
            'strength': str ('weak'|'medium'|'strong')
        }
    """
    errors = []

    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")

    if not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")

    if not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")

    if not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one digit")

    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        errors.append("Password must contain at least one special character")

    # Calculate strength
    strength = "weak"
    if len(errors) == 0:
        if len(password) >= 12:
            strength = "strong"
        elif len(password) >= 10:
            strength = "medium"

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "strength": strength,
    }
