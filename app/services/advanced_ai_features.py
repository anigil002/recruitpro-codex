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
        "description": "Structured conversation flow used by Abdulla Nigil for verbal screening.",
        "tags": ["screening", "egis", "interview"],
        "prompt": "\n".join(
            [
                "You are Abdulla Nigil, Regional Talent Acquisition Manager at Egis.",
                "Generate a value-based verbal screening script following the Egis format for the role: {ROLE_TITLE}.",
                "The script must include: introduction, consent, candidate type flow, relevance questions, evidence of impact,",
                "motivation, decision enablers, closing statements, and an internal notes table as described in the system",
                "documentation.",
            ]
        ),
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

