"""File upload security service per STANDARD-SEC-003.

Provides file validation, virus scanning, and secure storage for uploaded files.
"""

import hashlib
import logging
import secrets
from pathlib import Path
from typing import Optional, Tuple

from fastapi import HTTPException, UploadFile, status

logger = logging.getLogger(__name__)

# File upload constraints
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5MB
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/msword",  # .doc
}
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc"}


class FileValidationError(Exception):
    """Raised when file validation fails."""
    pass


class VirusScanError(Exception):
    """Raised when virus scanning fails or detects malware."""
    pass


def generate_secure_filename(original_filename: str) -> str:
    """Generate a secure random filename preserving the extension.

    Args:
        original_filename: Original uploaded filename

    Returns:
        Secure random filename with extension

    Example:
        >>> generate_secure_filename("resume.pdf")
        'a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6.pdf'
    """
    # Extract extension
    ext = Path(original_filename).suffix.lower()
    if not ext or ext not in ALLOWED_EXTENSIONS:
        ext = ".pdf"  # Default to PDF

    # Generate random filename (32 characters hex)
    random_name = secrets.token_hex(16)
    return f"{random_name}{ext}"


def validate_file_type(file: UploadFile) -> None:
    """Validate uploaded file type against allowed MIME types and extensions.

    Args:
        file: Uploaded file object

    Raises:
        FileValidationError: If file type is not allowed
    """
    # Check MIME type
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise FileValidationError(
            f"Invalid file type: {file.content_type}. "
            f"Only PDF and DOCX files are allowed."
        )

    # Check extension
    if file.filename:
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise FileValidationError(
                f"Invalid file extension: {ext}. "
                f"Only {', '.join(ALLOWED_EXTENSIONS)} are allowed."
            )


def validate_file_size(content: bytes) -> None:
    """Validate file size against maximum allowed size.

    Args:
        content: File content bytes

    Raises:
        FileValidationError: If file size exceeds limit
    """
    file_size = len(content)
    if file_size > MAX_FILE_SIZE_BYTES:
        size_mb = file_size / (1024 * 1024)
        max_mb = MAX_FILE_SIZE_BYTES / (1024 * 1024)
        raise FileValidationError(
            f"File size ({size_mb:.2f}MB) exceeds maximum allowed size ({max_mb}MB)"
        )


def scan_for_viruses(content: bytes, filename: str) -> Tuple[bool, Optional[str]]:
    """Scan file content for viruses and malware.

    This is a stub implementation. In production, integrate with:
    - ClamAV daemon via python-clamav or clamd
    - VirusTotal API
    - Cloud-based scanning service

    Args:
        content: File content bytes
        filename: Original filename for logging

    Returns:
        Tuple of (is_clean: bool, threat_name: Optional[str])
        - (True, None) if file is clean
        - (False, "threat_name") if malware detected

    Raises:
        VirusScanError: If scanning service is unavailable
    """
    # Calculate file hash for logging
    file_hash = hashlib.sha256(content).hexdigest()

    logger.info(
        f"Virus scan initiated for file: {filename} "
        f"(size: {len(content)} bytes, sha256: {file_hash})"
    )

    # TODO: Integrate with actual virus scanning service
    # Example ClamAV integration:
    # try:
    #     import clamd
    #     cd = clamd.ClamAVDaemon()
    #     scan_result = cd.scan_stream(content)
    #     if scan_result['stream'][0] == 'FOUND':
    #         threat = scan_result['stream'][1]
    #         logger.warning(f"Virus detected: {threat} in {filename}")
    #         return False, threat
    #     return True, None
    # except Exception as e:
    #     logger.error(f"Virus scan failed: {e}")
    #     raise VirusScanError(f"Virus scanning service unavailable: {e}")

    # Stub implementation - ALWAYS returns clean
    # IMPORTANT: Replace with actual scanning before production deployment
    logger.warning(
        "SECURITY WARNING: Virus scanning is not implemented. "
        "File passed without scanning. Integrate ClamAV or VirusTotal for production."
    )

    # For now, accept all files (development only)
    logger.info(f"Virus scan completed (stub): {filename} - CLEAN (not actually scanned)")
    return True, None


def validate_and_scan_file(file: UploadFile) -> Tuple[bytes, str]:
    """Validate and scan uploaded file for security.

    Performs:
    1. File type validation (MIME type and extension)
    2. File size validation
    3. Virus scanning
    4. Secure filename generation

    Args:
        file: Uploaded file object

    Returns:
        Tuple of (file_content: bytes, secure_filename: str)

    Raises:
        HTTPException: If validation or scanning fails
    """
    try:
        # Read file content
        content = file.file.read()
        file.file.seek(0)  # Reset file pointer

        # Validate file type
        try:
            validate_file_type(file)
        except FileValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

        # Validate file size
        try:
            validate_file_size(content)
        except FileValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

        # Scan for viruses
        try:
            is_clean, threat_name = scan_for_viruses(content, file.filename or "unknown")
            if not is_clean:
                logger.warning(
                    f"Malware detected in upload: {file.filename}, threat: {threat_name}"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File rejected: Malware detected ({threat_name})"
                )
        except VirusScanError as e:
            # Fail closed - reject file if scanning unavailable
            logger.error(f"Virus scan service unavailable: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="File upload temporarily unavailable (security service down)"
            )

        # Generate secure filename
        secure_filename = generate_secure_filename(file.filename or "upload.pdf")

        logger.info(
            f"File validation successful: {file.filename} -> {secure_filename} "
            f"({len(content)} bytes)"
        )

        return content, secure_filename

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error during file validation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File upload failed due to internal error"
        )
