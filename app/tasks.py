"""
Background Tasks

This module defines all background tasks that can be queued for asynchronous processing.
Tasks are executed by RQ workers and should be idempotent where possible.

Usage:
    from app.queue import enqueue_job

    # Enqueue a task
    job = enqueue_job('app.tasks.screen_candidate_async', candidate_id='c123')
"""

import logging
from typing import Any, Dict

from rq import get_current_job

logger = logging.getLogger(__name__)


def screen_candidate_async(candidate_id: str, position_id: str, user_id: str) -> Dict[str, Any]:
    """
    Background task for AI candidate screening.

    Args:
        candidate_id: Candidate ID to screen
        position_id: Position ID to screen against
        user_id: User ID who initiated the screening

    Returns:
        Dict with screening results
    """
    job = get_current_job()
    logger.info(f"[Job {job.id}] Starting candidate screening: {candidate_id}")

    try:
        # Import here to avoid circular dependencies
        from app.database import get_session
        from app.services.ai_helpers import screen_candidate_full

        with get_session() as session:
            # Get candidate and position
            from app.models.candidate import Candidate
            from app.models.position import Position

            candidate = session.query(Candidate).filter_by(candidate_id=candidate_id).first()
            position = session.query(Position).filter_by(position_id=position_id).first()

            if not candidate:
                raise ValueError(f"Candidate not found: {candidate_id}")
            if not position:
                raise ValueError(f"Position not found: {position_id}")

            # Perform screening
            result = screen_candidate_full(candidate, position, session)

            logger.info(f"[Job {job.id}] Screening completed: {candidate_id}")
            return result

    except Exception as e:
        logger.error(f"[Job {job.id}] Screening failed: {e}")
        raise


def analyze_document_async(file_path: str, document_type: str) -> Dict[str, Any]:
    """
    Background task for AI document analysis.

    Args:
        file_path: Path to document file
        document_type: Type of document ('cv', 'jd', etc.)

    Returns:
        Dict with analysis results
    """
    job = get_current_job()
    logger.info(f"[Job {job.id}] Starting document analysis: {file_path}")

    try:
        # Import here to avoid circular dependencies
        from app.services.ai_helpers import analyze_document

        result = analyze_document(file_path, document_type)

        logger.info(f"[Job {job.id}] Document analysis completed: {file_path}")
        return result

    except Exception as e:
        logger.error(f"[Job {job.id}] Document analysis failed: {e}")
        raise


def generate_outreach_async(candidate_id: str, position_id: str, template_type: str) -> Dict[str, Any]:
    """
    Background task for generating outreach emails.

    Args:
        candidate_id: Candidate ID
        position_id: Position ID
        template_type: Template type ('initial', 'follow_up', etc.')

    Returns:
        Dict with generated email content
    """
    job = get_current_job()
    logger.info(f"[Job {job.id}] Starting outreach generation: {candidate_id}")

    try:
        from app.database import get_session
        from app.services.ai_helpers import generate_outreach_email

        with get_session() as session:
            from app.models.candidate import Candidate
            from app.models.position import Position

            candidate = session.query(Candidate).filter_by(candidate_id=candidate_id).first()
            position = session.query(Position).filter_by(position_id=position_id).first()

            if not candidate:
                raise ValueError(f"Candidate not found: {candidate_id}")
            if not position:
                raise ValueError(f"Position not found: {position_id}")

            result = generate_outreach_email(candidate, position, template_type)

            logger.info(f"[Job {job.id}] Outreach generation completed: {candidate_id}")
            return result

    except Exception as e:
        logger.error(f"[Job {job.id}] Outreach generation failed: {e}")
        raise


def market_research_async(position_title: str, location: str) -> Dict[str, Any]:
    """
    Background task for market research and salary benchmarking.

    Args:
        position_title: Job title to research
        location: Location for research

    Returns:
        Dict with research results
    """
    job = get_current_job()
    logger.info(f"[Job {job.id}] Starting market research: {position_title}")

    try:
        from app.services.research import perform_market_research

        result = perform_market_research(position_title, location)

        logger.info(f"[Job {job.id}] Market research completed: {position_title}")
        return result

    except Exception as e:
        logger.error(f"[Job {job.id}] Market research failed: {e}")
        raise


def scan_file_for_viruses_async(file_path: str) -> Dict[str, Any]:
    """
    Background task for virus scanning uploaded files.

    Args:
        file_path: Path to file to scan

    Returns:
        Dict with scan results {'clean': bool, 'threats': list}
    """
    job = get_current_job()
    logger.info(f"[Job {job.id}] Starting virus scan: {file_path}")

    try:
        from app.services.security import scan_file_with_clamav

        result = scan_file_with_clamav(file_path)

        if not result["clean"]:
            logger.warning(f"[Job {job.id}] Threats detected: {result['threats']}")
        else:
            logger.info(f"[Job {job.id}] File clean: {file_path}")

        return result

    except Exception as e:
        logger.error(f"[Job {job.id}] Virus scan failed: {e}")
        raise


def bulk_import_candidates_async(file_path: str, project_id: str, user_id: str) -> Dict[str, Any]:
    """
    Background task for bulk importing candidates from file.

    Args:
        file_path: Path to import file (CSV, Excel)
        project_id: Project to import into
        user_id: User performing the import

    Returns:
        Dict with import results
    """
    job = get_current_job()
    logger.info(f"[Job {job.id}] Starting bulk import: {file_path}")

    try:
        from app.services.import_helpers import import_candidates_from_file

        result = import_candidates_from_file(file_path, project_id, user_id)

        logger.info(f"[Job {job.id}] Bulk import completed: {result['imported']} candidates")
        return result

    except Exception as e:
        logger.error(f"[Job {job.id}] Bulk import failed: {e}")
        raise


# Example: Task with retry on specific exceptions
def unreliable_api_call_async(api_url: str) -> Dict[str, Any]:
    """
    Example task that demonstrates retry logic for unreliable operations.

    This task will automatically retry on failure with exponential backoff
    (configured in queue.enqueue_job).
    """
    job = get_current_job()
    logger.info(f"[Job {job.id}] Calling API: {api_url}")

    import httpx

    try:
        response = httpx.get(api_url, timeout=30)
        response.raise_for_status()

        logger.info(f"[Job {job.id}] API call successful")
        return response.json()

    except httpx.HTTPError as e:
        logger.error(f"[Job {job.id}] API call failed: {e}")
        # This will trigger a retry
        raise
