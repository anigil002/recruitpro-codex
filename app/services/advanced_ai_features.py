"""Utilities for managing advanced AI feature toggles, prompt packs and embeddings.

This module brings together a couple of concepts described in the
`recruitpro_system_v2.5.md` specification:

* Persistent feature toggles that let administrators enable/disable
  experimental AI capabilities.
* Prompt packs – reusable prompt templates that power the outreach
  and screening assistants.
* References to embedding indexes that can be hydrated by external
  workers or vector databases.

The helpers below keep the implementation lightweight and database
backed so that the application behaves like a production-ready system
instead of relying on hard coded mock data.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from ..models import AdvancedFeaturesConfig, EmbeddingIndexRef
from ..utils.security import generate_id

# ---------------------------------------------------------------------------
# Default feature toggles
# ---------------------------------------------------------------------------

# The defaults mirror the capabilities described in the v2.5 system document.
DEFAULT_FEATURE_FLAGS: Dict[str, Any] = {
    "chatbot.tool_suggestions": {
        "market_research": True,
        "salary_benchmark": True,
        "bulk_outreach": True,
    },
    "sourcing.smartrecruiters_enabled": True,
    "screening.require_ai_score": True,
    "documents.auto_analyze_on_upload": True,
    "research.auto_run_market_research": True,
}


# ---------------------------------------------------------------------------
# Prompt packs (Verbal screening + outreach templates)
# ---------------------------------------------------------------------------

PROMPT_PACKS: List[Dict[str, Any]] = [
    {
        "slug": "verbal_screening_script",
        "name": "Verbal Screening Script (Egis format)",
        "category": "screening",
        "description": "Structured 20-30 minute conversation flow for Senior Talent Acquisition Partner conducting insight-driven, candidate-centric screening calls.",
        "tags": ["screening", "egis", "interview"],
        "prompt": """ROLE & GOAL
Persona:
Act as a Senior Talent Acquisition Partner conducting insight-driven, conversational, candidate-centric screening calls.
You never ask candidates to repeat what's already in the CV — you probe for depth, behaviour, ownership, decisions, impact, and motivation.
Primary Goal:
Generate a complete, structured, conversational 20–30 minute verbal screening script tailored to the JD, CV, role seniority, and leadership expectations.
The script must support a strong, evidence-based submission report.

INPUTS
• [Candidate CV]
• [Job Description]
• [Job Title]
• (Optional) Company Info → use placeholder if missing

AI EXECUTION RULES
• No repeating CV bullet points
• Always probe for context, ownership, challenges
• Keep tone natural and recruiter-friendly
• No engineering-level technical questions
• Adapt to seniority (Junior → VP)
• Trigger red-flag questions when needed, not by default

🔵 STRUCTURE OF THE SCRIPT (20–30 MINUTES)

PART 1: PRE-CALL RECRUITER CHECKLIST (INTERNAL)
Before generating the script:
1. Extract top 3–4 JD requirements
2. Identify 2–3 CV achievements aligned to JD
3. Determine seniority level:
   o Junior IC
   o Senior IC
   o Lead / Principal
   o Team Lead
   o Manager
   o Director / VP
4. Assess stakeholder/client-facing components
5. Scan for red flags:
   o job hopping
   o gaps
   o lateral moves
   o vague results
   o overqualification
6. Keep LinkedIn open

PART 2: VERBAL SCREENING SCRIPT

SECTION 1 — INTRODUCTION, PURPOSE & JOB OVERVIEW (3–4 mins)
"Hi [Candidate Name], this is Abdulla Nigil. I lead Talent Acquisition for the Egis North America region, based in our Dubai office.
Thank you for taking the time today — how are you doing?"
Purpose:
"This call is typically 20–30 minutes. I'd like to understand your background at a high level, connect it to the role, understand your motivations, and give you a clear view of the opportunity. Very conversational."
Job Overview:
"To set the context, this [Job Title] role focuses on [insert core purpose from JD].
Key responsibilities include [2–3 major duties], and it involves close collaboration with [key stakeholders].
We'll connect this with your experience shortly."
Transition:
"Does that make sense?"

SECTION 2 — CORE EXPERIENCE & JD ALIGNMENT (10–12 mins)
This section focuses on deeper behavioural, ownership, and impact-based questioning.
For each top 3–4 JD requirement, ask:
Lead-ins + Probing Questions:
• "Walk me through a situation where you handled something similar."
• "What part did you personally own?"
• "What made it complex behind the scenes?"
• "How did you navigate challenges in that scenario?"
• "What measurable impact did your involvement have?"
• "If you could redo it today, what would you change?"
This section sets the foundation for later leadership and interpretation assessment.

SECTION 3 — LEADERSHIP, TEAMING & STAKEHOLDER / CLIENT MANAGEMENT (4–6 mins)
(Use only the relevant categories based on JD + seniority.)
If Leadership is required:
• "Tell me about giving difficult feedback — how did you approach it?"
• "Describe a time someone wasn't performing — what did you do?"
• "How do you choose what to delegate and what to personally handle?"
If Team Collaboration (IC role):
• "Tell me about a strong cross-functional collaboration — what made it effective?"
• "How did you adapt to someone's working style?"
If Stakeholder / Client-facing:
• "Walk me through a difficult stakeholder situation — what made it challenging?"
• "How do you build trust with clients or senior stakeholders?"
• "How do you prepare for high-stakes external reviews or presentations?"

🔵 SECTION 4 — ROLE-SPECIFIC ADAPTIVE QUESTIONS (5–7 mins)
(Select only ONE category based on seniority — do not mix.)

🌱 Junior IC (0–3 yrs)
• "Tell me about a time you were stuck — how did you get unstuck?"
• "Describe feedback that stung — what did you do with it?"
• "Biggest mistake last year — what changed after?"

🔧 Senior IC (4–8 yrs)
• "Tell me about a significant decision you made without management input."
• "Have you mentored juniors? What did they struggle with?"
• "What does your manager never have to worry about when you're on a project?"

🧭 Lead / Principal IC (8+ yrs)
• "Tell me about a time you changed a project's direction — what resistance did you face?"
• "How do you influence decisions when you're not the formal authority?"
• "What's different about how you operate now versus five years ago?"

👥 Team Lead (2–5 reports)
• "Tell me about giving critical feedback — what was the outcome?"
• "Describe handling a non-performer."
• "How do you decide what to delegate?"

🏢 Manager (5+ reports)
• "Tell me about someone who wasn't working out — what actions did you take?"
• "Three critical projects, two capable people — how do you prioritise?"
• "Your philosophy on developing people who resist development?"

🧨 Director / VP (Executive Level)
Strategic Leadership & Direction
• "Tell me about reshaping strategy — what triggered the shift?"
• "What long-term vs short-term tradeoffs have you had to balance?"
Executive Accountability
• "Walk me through a high-stakes situation where the outcome fell on you."
• "What's a failure at this level that shaped your leadership?"
Leading Leaders
• "Tell me about developing a leader who elevated performance."
• "How do you coach leaders to operate independently?"
C-Suite / Board / Client Steering
• "Describe managing a difficult executive or board stakeholder."
• "How do you deliver unwelcome news upwards without losing trust?"
Transformation & Change
• "Tell me about leading major organisational change — what resistance did you face?"
Commercial & Risk
• "Tell me about a commercial risk you owned and how it played out."

SECTION 5 — CANDIDATE INTERPRETATION & ALIGNMENT (4–5 mins)
"Now that we've discussed your experience in detail, I'd like to hear your view of the role."
Primary Question:
"In your own words, what do you see as the core responsibilities of this position?"
Follow-ups:
• "What do you think are the most important priorities or challenges?"
• "Where do you see yourself having the strongest impact from day one?"
• (For senior roles)
"If you were stepping in tomorrow, what would your first 60–90 days look like?"
Transition:
"Great — let's talk about your motivations."

SECTION 6 — MOTIVATION PRESSURE-TEST (4–5 mins)
Pick 2–3:
• "Walk me through your last job move — what did you expect and what turned out different?"
• "What's the ONE thing about this role that would make you say no?"
• "If you received three offers tomorrow — what's your tiebreaker?"
• "What didn't work in your last role that you want to avoid here?"
• "What do you know about Egis beyond what's online?"

SECTION 7 — COMPENSATION & LOGISTICS (3–4 mins)
"What's your target compensation range (base + bonus)?"
If outside budget:
"Our range is around [X]. Knowing that, does it still make sense to continue?"
Other logistics:
• Notice period
• Relocation constraints
• Active interviews
• Timeline to move

SECTION 8 — CLOSING (1–2 mins)
"That covers everything from my side — what questions do you have for me?"
"I'll prepare a summary and share it with the hiring team. You'll hear back in the next few days."
"Great speaking with you — thanks again for your time."

RED FLAG DIAGNOSTIC MODULE (Internal Only — Trigger If Needed)
Job Hopping
"Walk me through your last two moves — what wasn't working?"
Career Gaps
"What were you focused on between [dates]?"
Lateral Moves
"You've moved between similar roles — what held back progression?"
Overqualified
"This seems like a step down — what's your thinking?"
Vague Achievements
"You led [X] — what measurable outcome did you own?"
Accountability
"Tell me about a failed project — what was your role?"
Peer Conflict
"Last difficult conversation with a colleague — what made it hard?"
Bad Decision
"Tell me about a decision that turned out wrong — how did you fix it?"
Difficult Stakeholder
"Most difficult stakeholder — what made them difficult?"

INTERNAL EXECUTION RULES
1. Never skip red-flag scan
2. Never accept polished answers — ask:
"That sounds rehearsed — what actually happened?"
3. Never postpone compensation discussions
4. Complete submission report within 30 minutes
5. Never recommend "maybe" without a clear validation plan

🟦 OUTPUT FORMAT (MANDATORY — FOLLOW THIS EXACTLY)

🔵 1. Pre-Call Checklist (Internal Use Only)
Provide:
• JD Must-Haves (3–4)
• Aligned CV Achievements (2–3)
• Seniority Category Selected (Junior / Senior / Lead / Manager / Director/VP)
• Stakeholder Requirements
• Potential Red Flags
• Recruiter Notes (1–2 lines)

🔵 2. Full Verbal Screening Script (Candidate-Facing)
Use the exact structure:
Section 1 — Introduction, Purpose & Job Overview
(Include the prepared text)
Section 2 — Core Experience & JD Alignment
(List ALL questions the recruiter must ask)
Section 3 — Leadership / Teaming / Stakeholder Questions
(Include only what applies)
Section 4 — Role-Specific Adaptive Questions
(Include ONLY the chosen seniority block)
Section 5 — Candidate Interpretation
(List the 3–4 interpretation questions)
Section 6 — Motivation Pressure-Test
(Add selected questions)
Section 7 — Compensation & Logistics
(Add compensation + logistics questions)
Section 8 — Closing
(Add the closing lines)

🔵 3. Red Flag Follow-Up Questions (Internal)
Only show if red flags were detected.

🔵 4. Notes for Submission Report (Internal)
Provide:
• Key strengths (bullet points)
• Risks or gaps (bullet points)
• Recommended next step: Strong Proceed / Proceed with Conditions / Do Not Proceed""",
    },
    {
        "slug": "outreach_email_standard",
        "name": "Outreach Email – Standard",
        "category": "outreach",
        "description": "Default outreach email template used for most roles.",
        "tags": ["outreach", "email", "standard"],
        "prompt": "Generate the standard outreach email from the RecruitPro spec using the provided candidate and role context.",
    },
    {
        "slug": "outreach_email_executive",
        "name": "Outreach Email – Executive",
        "category": "outreach",
        "description": "Executive/leadership focused outreach email template.",
        "tags": ["outreach", "email", "executive"],
        "prompt": "Generate the executive outreach email variant from the RecruitPro spec using the provided context.",
    },
    {
        "slug": "outreach_email_technical",
        "name": "Outreach Email – Technical",
        "category": "outreach",
        "description": "Technical/project specialist outreach template.",
        "tags": ["outreach", "email", "technical"],
        "prompt": "Generate the technical outreach email variant from the RecruitPro spec using the provided context.",
    },
]


# ---------------------------------------------------------------------------
# Feature toggle helpers
# ---------------------------------------------------------------------------

def list_feature_flags(session: Session) -> List[Dict[str, Any]]:
    """Return all feature flags merged with defaults.

    Each item exposes whether the value is overridden in the database so the
    admin UI can highlight customisations.
    """

    stored: Dict[str, AdvancedFeaturesConfig] = {
        row.key: row for row in session.query(AdvancedFeaturesConfig).all()
    }
    flags: List[Dict[str, Any]] = []

    for key, default in DEFAULT_FEATURE_FLAGS.items():
        record = stored.get(key)
        flags.append(
            {
                "key": key,
                "value": record.value_json if record else default,
                "overridden": record is not None,
                "updated_at": record.updated_at if record else None,
                "updated_by": record.updated_by if record else None,
            }
        )

    for key, record in stored.items():
        if key in DEFAULT_FEATURE_FLAGS:
            continue
        flags.append(
            {
                "key": key,
                "value": record.value_json,
                "overridden": True,
                "updated_at": record.updated_at,
                "updated_by": record.updated_by,
            }
        )

    flags.sort(key=lambda item: item["key"])
    return flags


def get_feature_flag(session: Session, key: str) -> Any:
    """Retrieve a feature flag or fall back to the default value."""

    record = session.get(AdvancedFeaturesConfig, key)
    if record:
        return record.value_json
    return DEFAULT_FEATURE_FLAGS.get(key)


def set_feature_flag(session: Session, key: str, value: Any, *, user_id: str) -> AdvancedFeaturesConfig:
    """Persist a feature flag override."""

    record = session.get(AdvancedFeaturesConfig, key)
    now = datetime.utcnow()
    if record:
        record.value_json = value
        record.updated_by = user_id
        record.updated_at = now
    else:
        record = AdvancedFeaturesConfig(
            key=key,
            value_json=value,
            updated_by=user_id,
            updated_at=now,
        )
        session.add(record)
    session.flush()
    return record


# ---------------------------------------------------------------------------
# Prompt packs
# ---------------------------------------------------------------------------

def list_prompt_packs() -> List[Dict[str, Any]]:
    """Return all available prompt packs."""

    return PROMPT_PACKS


def get_prompt_pack(slug: str) -> Optional[Dict[str, Any]]:
    """Return a prompt pack by slug."""

    for pack in PROMPT_PACKS:
        if pack["slug"] == slug:
            return pack
    return None


# ---------------------------------------------------------------------------
# Embedding index helpers
# ---------------------------------------------------------------------------

def list_embedding_indices(session: Session) -> List[Dict[str, Any]]:
    """Return embedding index metadata sorted by recency."""

    records = (
        session.query(EmbeddingIndexRef)
        .order_by(EmbeddingIndexRef.created_at.desc())
        .all()
    )
    return [
        {
            "index_id": record.index_id,
            "name": record.name,
            "description": record.description,
            "vector_dim": record.vector_dim,
            "location_uri": record.location_uri,
            "created_by": record.created_by,
            "created_at": record.created_at,
        }
        for record in records
    ]


def register_embedding_index(
    session: Session, payload: Dict[str, Any], *, user_id: str
) -> EmbeddingIndexRef:
    """Register a new embedding index reference."""

    record = EmbeddingIndexRef(
        index_id=generate_id(),
        name=payload["name"],
        description=payload.get("description"),
        vector_dim=payload["vector_dim"],
        location_uri=payload["location_uri"],
        created_by=user_id,
        created_at=datetime.utcnow(),
    )
    session.add(record)
    session.flush()
    return record


__all__ = [
    "DEFAULT_FEATURE_FLAGS",
    "list_feature_flags",
    "get_feature_flag",
    "set_feature_flag",
    "list_prompt_packs",
    "get_prompt_pack",
    "list_embedding_indices",
    "register_embedding_index",
]

