"""AI-related endpoints."""

from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import Candidate, Position, Project
from ..schemas import (
    CallScriptRequest,
    CallScriptResponse,
    ChatbotMessageRequest,
    ChatbotMessageResponse,
    OutreachRequest,
    OutreachResponse,
    SalaryBenchmarkRequest,
    SalaryBenchmarkResponse,
)
from ..services.activity import log_activity
from ..services.ai import (
    analyze_file_stub,
    enqueue_ai_job,
    generate_call_script_stub,
    generate_email_stub,
    generate_jd_stub,
    generate_salary_stub,
    record_screening,
)
from ..utils.security import generate_id

router = APIRouter(prefix="/api", tags=["ai"])


@router.post("/ai/analyze-file")
def analyze_file(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Dict[str, Any]:
    file_name = payload.get("filename", "Uploaded File")
    result = analyze_file_stub(file_name)
    enqueue_ai_job(
        db,
        "file_analysis",
        project_id=payload.get("project_id"),
        request=payload,
        response=result,
    )
    return result


@router.post("/ai/generate-jd")
def generate_jd_endpoint(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Dict[str, Any]:
    title = payload.get("title")
    if not title:
        raise HTTPException(status_code=400, detail="title is required")
    jd = generate_jd_stub(title)
    enqueue_ai_job(db, "generate_jd", position_id=payload.get("position_id"), request=payload, response=jd)
    return jd


@router.post("/ai/source-candidates")
def source_candidates(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Dict[str, Any]:
    job = enqueue_ai_job(db, "ai_sourcing", project_id=payload.get("project_id"), request=payload, response={"found": 3})
    log_activity(
        db,
        actor_type="ai",
        actor_id=current_user.user_id,
        project_id=payload.get("project_id"),
        message="AI sourcing completed (stub)",
        event_type="ai_sourcing",
    )
    return {"job_id": job.job_id, "found": 3}


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

    score = {
        "match": 0.7,
        "highlights": ["Experienced recruiter"],
    }
    record_screening(db, candidate, position_id, score)
    enqueue_ai_job(db, "ai_screening", candidate_id=candidate_id, position_id=position_id, request=payload, response=score)
    log_activity(
        db,
        actor_type="ai",
        actor_id=current_user.user_id,
        project_id=candidate.project_id,
        position_id=position_id,
        candidate_id=candidate_id,
        message="Candidate screened (stub)",
        event_type="ai_screening",
    )
    candidate.ai_score = score
    db.add(candidate)
    return score


@router.post("/ai/generate-email", response_model=OutreachResponse)
def generate_email(
    payload: OutreachRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> OutreachResponse:
    email = generate_email_stub(payload.dict())
    enqueue_ai_job(db, "generate_email", request=payload.dict(), response=email)
    return OutreachResponse(**email)


@router.post("/ai/call-script", response_model=CallScriptResponse)
def generate_call_script(
    payload: CallScriptRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> CallScriptResponse:
    script = generate_call_script_stub(payload.dict())
    enqueue_ai_job(db, "call_script", request=payload.dict(), response=script)
    return CallScriptResponse(**script)


@router.post("/research/salary-benchmark", response_model=SalaryBenchmarkResponse)
def salary_benchmark(
    payload: SalaryBenchmarkRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> SalaryBenchmarkResponse:
    result = generate_salary_stub(payload.dict())
    enqueue_ai_job(db, "salary_benchmark", request=payload.dict(), response=result)
    return SalaryBenchmarkResponse(**result)


@router.post("/chatbot", response_model=ChatbotMessageResponse)
def chatbot(
    payload: ChatbotMessageRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ChatbotMessageResponse:
    session_id = payload.session_id or generate_id()
    reply = f"You said: {payload.message}. (This is a stubbed chatbot response.)"
    enqueue_ai_job(
        db,
        "chatbot",
        request={"session_id": session_id, "message": payload.message},
        response={"reply": reply},
    )
    return ChatbotMessageResponse(session_id=session_id, reply=reply, tools_suggested=[])


@router.post("/research/market-analysis")
def market_analysis(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Dict[str, Any]:
    enqueue_ai_job(db, "market_research", project_id=payload.get("project_id"), request=payload, response={"status": "completed"})
    return {"status": "completed"}
