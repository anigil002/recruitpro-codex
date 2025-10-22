"""AI orchestration utilities that wrap the Gemini service and worker queue."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy.orm import Session

from ..database import get_session
from ..models import (
    AIJob,
    Candidate,
    Project,
    ProjectDocument,
    ProjectMarketResearch,
    SalaryBenchmark,
    ScreeningRun,
    SourcingJob,
    SourcingResult,
)
from ..utils.security import generate_id
from ..utils.storage import resolve_storage_path
from .activity import log_activity
from .gemini import CandidatePersona, gemini
from .queue import background_queue
from .realtime import events


# ---------------------------------------------------------------------------
# Job lifecycle helpers
# ---------------------------------------------------------------------------

def create_ai_job(
    session: Session,
    job_type: str,
    *,
    project_id: Optional[str] = None,
    position_id: Optional[str] = None,
    candidate_id: Optional[str] = None,
    request: Optional[Dict[str, Any]] = None,
    status: str = "pending",
) -> AIJob:
    job = AIJob(
        job_id=generate_id(),
        job_type=job_type,
        project_id=project_id,
        position_id=position_id,
        candidate_id=candidate_id,
        status=status,
        request_json=request,
        created_at=datetime.utcnow(),
    )
    session.add(job)
    session.flush()
    return job


def mark_job_running(session: Session, job: AIJob) -> None:
    job.status = "running"
    job.updated_at = datetime.utcnow()
    session.add(job)


def mark_job_completed(session: Session, job: AIJob, response: Dict[str, Any]) -> None:
    job.status = "completed"
    job.response_json = response
    job.updated_at = datetime.utcnow()
    session.add(job)
    events.publish_sync({"type": "job", "user_id": None, "payload": {"job_id": job.job_id, "status": job.status}})


def mark_job_failed(session: Session, job: AIJob, error: str) -> None:
    job.status = "failed"
    job.error = error
    job.updated_at = datetime.utcnow()
    session.add(job)
    events.publish_sync(
        {"type": "job", "user_id": None, "payload": {"job_id": job.job_id, "status": job.status, "error": error}}
    )


# ---------------------------------------------------------------------------
# Queue handlers
# ---------------------------------------------------------------------------

def _handle_file_analysis_job(payload: Dict[str, Any]) -> None:
    job_id = payload["job_id"]
    with get_session() as session:
        job = session.get(AIJob, job_id)
        if not job:
            return
        mark_job_running(session, job)
        request = job.request_json or {}
        document_id = request.get("document_id")
        document = session.get(ProjectDocument, document_id) if request.get("project_document") else None
        if not document:
            # Fallback to the generic document table
            from ..models import Document

            document = session.get(Document, document_id)
        if not document:
            mark_job_failed(session, job, "Document not found")
            return
        project = session.get(Project, request.get("project_id") or getattr(document, "project_id", None))
        try:
            path = resolve_storage_path(document.file_url)
        except ValueError:
            mark_job_failed(session, job, "Document path outside storage directory")
            return
        analysis = gemini.analyze_file(
            path,
            original_name=document.filename,
            mime_type=document.mime_type,
            project_context={
                "name": getattr(project, "name", None),
                "summary": getattr(project, "summary", None),
                "sector": getattr(project, "sector", None),
                "location_region": getattr(project, "location_region", None),
                "client": getattr(project, "client", None),
            }
            if project
            else {},
        )
        # Update project metadata
        if project and analysis["project_info"]:
            info = analysis["project_info"]
            for field in ("name", "summary", "sector", "location_region", "client"):
                value = info.get(field)
                if value:
                    setattr(project, field, value)
            session.add(project)
        # Create draft positions
        if project:
            from ..models import Position

            existing_titles = {pos.title for pos in project.positions}
            for role in analysis["positions"]:
                if role["title"] in existing_titles:
                    continue
                position = Position(
                    position_id=generate_id(),
                    project_id=project.project_id,
                    title=role["title"],
                    department=role.get("department"),
                    experience=role.get("experience"),
                    responsibilities=role.get("responsibilities"),
                    requirements=role.get("requirements"),
                    location=role.get("location"),
                    description=role.get("description"),
                    status="draft",
                )
                session.add(position)
                existing_titles.add(role["title"])
        mark_job_completed(session, job, analysis)
        if project:
            log_activity(
                session,
                actor_type="ai",
                actor_id=request.get("user_id"),
                project_id=project.project_id,
                message=f"Analyzed document {document.filename}",
                event_type="file_analyzed",
            )
            if request.get("trigger_market_research") and not project.research_done:
                enqueue_market_research_job(session, project.project_id, request.get("user_id"))


def _handle_market_research_job(payload: Dict[str, Any]) -> None:
    job_id = payload["job_id"]
    with get_session() as session:
        job = session.get(AIJob, job_id)
        if not job:
            return
        mark_job_running(session, job)
        request = job.request_json or {}
        project = session.get(Project, request.get("project_id"))
        research = gemini.generate_market_research(request)
        record = ProjectMarketResearch(
            research_id=generate_id(),
            project_id=request.get("project_id"),
            region=research["region"],
            window=f"{datetime.utcnow().year}",
            findings=research["findings"],
            sources=research["sources"],
            status="completed",
            completed_at=datetime.utcnow(),
        )
        session.add(record)
        if project:
            project.research_done = 1
            project.research_status = "completed"
            session.add(project)
        mark_job_completed(session, job, research)
        log_activity(
            session,
            actor_type="ai",
            actor_id=request.get("user_id"),
            project_id=request.get("project_id"),
            message="Market research package ready",
            event_type="market_research",
        )


def _handle_sourcing_job(payload: Dict[str, Any]) -> None:
    job_id = payload["job_id"]
    sourcing_job_id = payload.get("sourcing_job_id")
    with get_session() as session:
        job = session.get(AIJob, job_id)
        sourcing_job = session.get(SourcingJob, sourcing_job_id) if sourcing_job_id else None
        if not job:
            return
        mark_job_running(session, job)
        request = job.request_json or {}
        persona = CandidatePersona(
            title=request.get("title", "Project Manager"),
            location=request.get("location"),
            skills=request.get("skills"),
            seniority=request.get("seniority"),
        )
        boolean_search = gemini.build_boolean_search(persona)
        profiles = gemini.synthesise_candidate_profiles(persona, count=6)
        if sourcing_job:
            sourcing_job.status = "completed"
            sourcing_job.progress = 100
            sourcing_job.found_count = len(profiles)
            sourcing_job.updated_at = datetime.utcnow()
            session.add(sourcing_job)
            session.query(SourcingResult).filter(SourcingResult.sourcing_job_id == sourcing_job.sourcing_job_id).delete()
            for profile in profiles:
                session.add(
                    SourcingResult(
                        result_id=generate_id(),
                        sourcing_job_id=sourcing_job.sourcing_job_id,
                        platform=profile.get("platform", "LinkedIn"),
                        profile_url=profile["profile_url"],
                        name=profile["name"],
                        title=profile["title"],
                        company=profile.get("company"),
                        location=profile.get("location"),
                        summary=profile.get("summary"),
                        quality_score=profile.get("quality_score"),
                    )
                )
        response = {"search_string": boolean_search, "profiles": profiles}
        mark_job_completed(session, job, response)
        log_activity(
            session,
            actor_type="ai",
            actor_id=request.get("user_id"),
            project_id=request.get("project_id"),
            position_id=request.get("position_id"),
            message="AI sourcing completed",
            event_type="ai_sourcing",
        )


def _handle_linkedin_xray(payload: Dict[str, Any]) -> None:
    job_id = payload["job_id"]
    with get_session() as session:
        job = session.get(AIJob, job_id)
        if not job:
            return
        mark_job_running(session, job)
        request = job.request_json or {}
        persona = CandidatePersona(
            title=request.get("title", "Project Manager"),
            location=request.get("location"),
            skills=request.get("skills"),
            seniority=request.get("seniority"),
        )
        boolean_search = gemini.build_boolean_search(persona)
        response = {
            "boolean_search": boolean_search,
            "cse_url": f"https://www.google.com/search?q={boolean_search.replace(' ', '+')}",
        }
        mark_job_completed(session, job, response)
        log_activity(
            session,
            actor_type="ai",
            actor_id=request.get("user_id"),
            project_id=request.get("project_id"),
            message="LinkedIn X-Ray search generated",
            event_type="linkedin_xray",
        )


def _handle_smartrecruiters(payload: Dict[str, Any]) -> None:
    job_id = payload["job_id"]
    with get_session() as session:
        job = session.get(AIJob, job_id)
        if not job:
            return
        mark_job_running(session, job)
        request = job.request_json or {}
        plan = gemini.smartrecruiters_plan(request)
        mark_job_completed(session, job, plan)
        log_activity(
            session,
            actor_type="ai",
            actor_id=request.get("user_id"),
            project_id=request.get("project_id"),
            message="SmartRecruiters automation queued",
            event_type="smartrecruiters",
        )


background_queue.register_handler("file_analysis", _handle_file_analysis_job)
background_queue.register_handler("market_research", _handle_market_research_job)
background_queue.register_handler("ai_sourcing", _handle_sourcing_job)
background_queue.register_handler("linkedin_xray", _handle_linkedin_xray)
background_queue.register_handler("smartrecruiters_bulk", _handle_smartrecruiters)


# ---------------------------------------------------------------------------
# External helpers used by routers
# ---------------------------------------------------------------------------

def enqueue_market_research_job(session: Session, project_id: str, user_id: Optional[str]) -> AIJob:
    existing_job = (
        session.query(AIJob)
        .filter(AIJob.project_id == project_id, AIJob.job_type == "market_research", AIJob.status != "failed")
        .order_by(AIJob.created_at.desc())
        .first()
    )
    if existing_job and existing_job.status in {"pending", "running"}:
        return existing_job
    job = create_ai_job(
        session,
        "market_research",
        project_id=project_id,
        request={"project_id": project_id, "user_id": user_id},
    )
    session.flush()
    background_queue.enqueue("market_research", {"job_id": job.job_id})
    return job


def record_screening(session: Session, candidate: Candidate, position_id: str, score: Dict[str, Any]) -> ScreeningRun:
    run = ScreeningRun(
        screening_id=generate_id(),
        candidate_id=candidate.candidate_id,
        position_id=position_id,
        score_json=score,
        created_at=datetime.utcnow(),
    )
    session.add(run)
    return run


def get_or_create_salary_benchmark(
    session: Session,
    payload: Dict[str, Any],
    *,
    user_id: str,
) -> SalaryBenchmark:
    benchmark = (
        session.query(SalaryBenchmark)
        .filter(
            SalaryBenchmark.title == payload.get("title"),
            SalaryBenchmark.region == payload.get("region"),
            SalaryBenchmark.sector == payload.get("sector"),
            SalaryBenchmark.seniority == payload.get("seniority"),
        )
        .first()
    )
    if benchmark:
        return benchmark
    result = gemini.generate_salary_benchmark(payload)
    benchmark = SalaryBenchmark(
        benchmark_id=generate_id(),
        title=payload.get("title"),
        region=payload.get("region"),
        sector=payload.get("sector"),
        seniority=payload.get("seniority"),
        currency=result["currency"],
        annual_min=result["annual_min"],
        annual_mid=result["annual_mid"],
        annual_max=result["annual_max"],
        rationale=result["rationale"],
        sources=result["sources"],
        created_by=user_id,
    )
    session.add(benchmark)
    mark_job = create_ai_job(
        session,
        "salary_benchmark",
        project_id=payload.get("project_id"),
        request=payload,
        status="completed",
    )
    mark_job_completed(session, mark_job, result)
    return benchmark


def start_sourcing_job(
    session: Session,
    payload: Dict[str, Any],
    *,
    user_id: str,
) -> Dict[str, Any]:
    sourcing_job = SourcingJob(
        sourcing_job_id=generate_id(),
        project_id=payload.get("project_id"),
        position_id=payload.get("position_id"),
        params_json=payload,
        status="pending",
        created_at=datetime.utcnow(),
    )
    session.add(sourcing_job)
    job = create_ai_job(
        session,
        "ai_sourcing",
        project_id=payload.get("project_id"),
        position_id=payload.get("position_id"),
        request={**payload, "user_id": user_id},
    )
    session.flush()
    background_queue.enqueue("ai_sourcing", {"job_id": job.job_id, "sourcing_job_id": sourcing_job.sourcing_job_id})
    return {"job": job, "sourcing_job": sourcing_job}


def start_linkedin_xray(session: Session, payload: Dict[str, Any], user_id: str) -> AIJob:
    job = create_ai_job(
        session,
        "linkedin_xray",
        project_id=payload.get("project_id"),
        request={**payload, "user_id": user_id},
    )
    session.flush()
    background_queue.enqueue("linkedin_xray", {"job_id": job.job_id})
    return job


def start_smartrecruiters_bulk(session: Session, payload: Dict[str, Any], user_id: str) -> AIJob:
    job = create_ai_job(
        session,
        "smartrecruiters_bulk",
        project_id=payload.get("project_id"),
        request={**payload, "user_id": user_id},
    )
    session.flush()
    background_queue.enqueue("smartrecruiters_bulk", {"job_id": job.job_id})
    return job


def analyze_document_inline(
    session: Session,
    document_id: str,
    *,
    project_id: Optional[str],
    user_id: Optional[str],
) -> Dict[str, Any]:
    from ..models import Document

    document = session.get(Document, document_id)
    if not document:
        raise ValueError("Document not found")
    project = session.get(Project, project_id) if project_id else None
    path = resolve_storage_path(document.file_url)
    analysis = gemini.analyze_file(
        path,
        original_name=document.filename,
        mime_type=document.mime_type,
        project_context={
            "name": getattr(project, "name", None),
            "summary": getattr(project, "summary", None),
            "sector": getattr(project, "sector", None),
            "location_region": getattr(project, "location_region", None),
            "client": getattr(project, "client", None),
        }
        if project
        else {},
    )
    job = create_ai_job(
        session,
        "file_analysis",
        project_id=project_id,
        request={"document_id": document_id, "user_id": user_id},
        status="completed",
    )
    mark_job_completed(session, job, analysis)
    return analysis


__all__ = [
    "create_ai_job",
    "mark_job_completed",
    "mark_job_failed",
    "record_screening",
    "get_or_create_salary_benchmark",
    "start_sourcing_job",
    "start_linkedin_xray",
    "start_smartrecruiters_bulk",
    "enqueue_market_research_job",
    "analyze_document_inline",
]
