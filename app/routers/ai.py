"""AI-related endpoints."""

from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import (
    Candidate,
    ChatbotMessage,
    ChatbotSession,
    OutreachRun,
    Position,
    Project,
    ProjectMarketResearch,
)
from ..schemas import (
    CallScriptRequest,
    CallScriptResponse,
    ChatbotMessageRequest,
    ChatbotMessageResponse,
    FileAnalysisRequest,
    FileAnalysisResponse,
    MarketResearchRequest,
    MarketResearchResponse,
    OutreachRequest,
    OutreachResponse,
    SalaryBenchmarkRequest,
    SalaryBenchmarkResponse,
)
from ..services.activity import log_activity
from ..services.ai import (
    analyze_document_inline,
    create_ai_job,
    enqueue_market_research_job,
    get_or_create_salary_benchmark,
    mark_job_completed,
    record_screening,
    start_sourcing_job,
)
from ..services.chatbot import chatbot_orchestrator
from ..services.gemini import gemini
from ..utils.security import generate_id

router = APIRouter(prefix="/api", tags=["ai"])


@router.post("/ai/analyze-file", response_model=FileAnalysisResponse)
def analyze_file(
    payload: FileAnalysisRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> FileAnalysisResponse:
    try:
        analysis = analyze_document_inline(
            db,
            payload.document_id,
            project_id=payload.project_id,
            user_id=current_user.user_id,
        )
    except ValueError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if payload.trigger_market_research and payload.project_id:
        enqueue_market_research_job(db, payload.project_id, current_user.user_id)
    return FileAnalysisResponse(**analysis)


@router.post("/ai/generate-jd")
def generate_jd_endpoint(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Dict[str, Any]:
    title = payload.get("title")
    if not title:
        raise HTTPException(status_code=400, detail="title is required")
    jd = gemini.generate_job_description(payload)
    job = create_ai_job(
        db,
        "generate_jd",
        position_id=payload.get("position_id"),
        request={**payload, "user_id": current_user.user_id},
    )
    mark_job_completed(db, job, jd)
    return jd


@router.post("/ai/source-candidates")
def source_candidates(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Dict[str, Any]:
    if not payload.get("project_id") or not payload.get("position_id"):
        raise HTTPException(status_code=400, detail="project_id and position_id required")
    result = start_sourcing_job(db, payload, user_id=current_user.user_id)
    sourcing_job = result["sourcing_job"]
    job = result["job"]
    return {
        "job_id": job.job_id,
        "status": job.status,
        "sourcing_job_id": sourcing_job.sourcing_job_id,
    }


@router.post("/ai/screen-candidate")
def screen_candidate(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Dict[str, Any]:
    candidate_id = payload.get("candidate_id")
    position_id = payload.get("position_id")
    if not candidate_id or not position_id:
        raise HTTPException(status_code=400, detail="candidate_id and position_id required")
    candidate = db.get(Candidate, candidate_id)
    position = db.get(Position, position_id)
    if not candidate or not position:
        raise HTTPException(status_code=404, detail="Candidate or position not found")

    score_payload = {
        "skills": payload.get("skills") or candidate.tags or [],
        "years_experience": payload.get("years_experience", 0),
        "leadership": payload.get("leadership", False),
    }
    score = gemini.score_candidate(score_payload)
    candidate.ai_score = score
    db.add(candidate)

    # Create minimal structured screening result for backwards compatibility
    # This endpoint uses simple scoring, not full CV analysis
    full_screening_result = {
        "candidate": {
            "name": candidate.name,
            "email": candidate.email,
            "phone": candidate.phone
        },
        "score": score
    }

    table_1 = {
        "overall_fit": "Potential Match",
        "recommended_roles": [position.title] if position else [],
        "key_strengths": ["Manual screening - see score details"],
        "potential_gaps": [],
        "notice_period": "Not Mentioned"
    }

    table_2 = [
        {
            "requirement_category": "Manual Screening",
            "requirement_description": "On-demand screening via API",
            "compliance_status": "⚠️ Not Mentioned / Cannot Confirm",
            "evidence": "This is a manual/API-based screening, not full CV analysis"
        }
    ]

    final_recommendation = {
        "summary": f"Manual screening completed with score: {score}. Full CV analysis not performed.",
        "decision": "Suitable for a lower-grade role"
    }

    record_screening(db, candidate, position_id, full_screening_result, table_1, table_2, final_recommendation)
    job = create_ai_job(
        db,
        "ai_screening",
        candidate_id=candidate_id,
        position_id=position_id,
        request={**payload, "user_id": current_user.user_id},
    )
    mark_job_completed(db, job, score)
    log_activity(
        db,
        actor_type="ai",
        actor_id=current_user.user_id,
        project_id=candidate.project_id,
        position_id=position_id,
        candidate_id=candidate_id,
        message="Candidate screened via AI",
        event_type="ai_screening",
    )
    return score


@router.post("/ai/generate-email", response_model=OutreachResponse)
def generate_email(
    payload: OutreachRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> OutreachResponse:
    email = gemini.generate_outreach_email(payload.dict())
    job = create_ai_job(db, "generate_email", request={**payload.dict(), "user_id": current_user.user_id})
    mark_job_completed(db, job, email)
    outreach = OutreachRun(
        outreach_id=generate_id(),
        user_id=current_user.user_id,
        candidate_id=None,
        position_id=None,
        type="email",
        output_json=email,
        created_at=datetime.utcnow(),
    )
    db.add(outreach)
    return OutreachResponse(**email)


@router.post("/ai/call-script", response_model=CallScriptResponse)
def generate_call_script(
    payload: CallScriptRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> CallScriptResponse:
    script = gemini.generate_call_script(payload.dict())
    job = create_ai_job(db, "call_script", request={**payload.dict(), "user_id": current_user.user_id})
    mark_job_completed(db, job, script)
    return CallScriptResponse(**script)


@router.post("/research/salary-benchmark", response_model=SalaryBenchmarkResponse)
def salary_benchmark(
    payload: SalaryBenchmarkRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> SalaryBenchmarkResponse:
    benchmark = get_or_create_salary_benchmark(db, payload.dict(), user_id=current_user.user_id)
    return SalaryBenchmarkResponse(
        currency=benchmark.currency,
        annual_min=benchmark.annual_min,
        annual_mid=benchmark.annual_mid,
        annual_max=benchmark.annual_max,
        rationale=benchmark.rationale,
        sources=benchmark.sources,
    )


@router.post("/chatbot", response_model=ChatbotMessageResponse)
def chatbot(
    payload: ChatbotMessageRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ChatbotMessageResponse:
    session: ChatbotSession | None = None
    if payload.session_id:
        session = db.get(ChatbotSession, payload.session_id)
    if not session:
        session = ChatbotSession(
            session_id=payload.session_id or generate_id(),
            user_id=current_user.user_id,
            context_json={},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(session)
    history = (
        db.query(ChatbotMessage)
        .filter(ChatbotMessage.session_id == session.session_id)
        .order_by(ChatbotMessage.created_at.asc())
        .all()
    )
    history_payload = [{"role": msg.role, "content": msg.content} for msg in history]

    user_message = ChatbotMessage(
        message_id=generate_id(),
        session_id=session.session_id,
        role="user",
        content=payload.message,
        created_at=datetime.utcnow(),
    )
    db.add(user_message)
    history.append(user_message)

    reply_payload = chatbot_orchestrator.handle_message(
        db,
        session,
        history_payload,
        user_id=current_user.user_id,
        message=payload.message,
    )

    assistant_message = ChatbotMessage(
        message_id=generate_id(),
        session_id=session.session_id,
        role="assistant",
        content=reply_payload["reply"],
        created_at=datetime.utcnow(),
    )
    db.add(assistant_message)
    session.updated_at = datetime.utcnow()
    db.add(session)
    job = create_ai_job(
        db,
        "chatbot",
        request={"session_id": session.session_id, "message": payload.message, "user_id": current_user.user_id},
    )
    mark_job_completed(db, job, reply_payload)
    return ChatbotMessageResponse(
        session_id=session.session_id,
        reply=reply_payload["reply"],
        tools_suggested=reply_payload.get("tools_suggested", []),
        context_echo=reply_payload.get("context_echo"),
    )


@router.post("/research/market-analysis")
def market_analysis(
    payload: MarketResearchRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    project = db.get(Project, payload.project_id)
    if not project or project.created_by != current_user.user_id:
        raise HTTPException(status_code=404, detail="Project not found")
    existing = (
        db.query(ProjectMarketResearch)
        .filter(ProjectMarketResearch.project_id == payload.project_id)
        .order_by(ProjectMarketResearch.completed_at.desc())
        .first()
    )
    if existing and existing.status == "completed":
        return MarketResearchResponse(
            region=existing.region,
            sector=project.sector or payload.sector or "",
            summary=project.summary,
            findings=existing.findings,
            sources=existing.sources,
        )
    job = enqueue_market_research_job(db, payload.project_id, current_user.user_id)
    return {"job_id": job.job_id, "status": job.status}


