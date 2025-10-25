"""Pydantic schemas for API payloads."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import AnyHttpUrl, BaseModel, EmailStr, Field, field_validator, model_validator


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str
    exp: int


class UserBase(BaseModel):
    email: EmailStr
    name: str
    role: str = Field(default="recruiter", pattern="^(recruiter|admin)$")


class UserCreate(UserBase):
    password: str = Field(min_length=8)


class UserRead(UserBase):
    role: str = Field(pattern="^(recruiter|admin|super_admin)$")
    user_id: str
    created_at: datetime
    settings: Optional[dict]


class UserUpdate(BaseModel):
    name: Optional[str] = None


class UserSettingsUpdate(BaseModel):
    settings: dict


class UserRoleUpdate(BaseModel):
    role: str = Field(pattern="^(recruiter|admin)$")


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ProjectBase(BaseModel):
    name: str
    sector: Optional[str] = None
    location_region: Optional[str] = None
    summary: Optional[str] = None
    client: Optional[str] = None
    status: Optional[str] = Field(default="active", pattern=r"^(active|on-hold|completed|archived)$")
    priority: Optional[str] = Field(default="medium", pattern=r"^(urgent|high|medium|low)$")
    department: Optional[str] = None
    tags: Optional[List[str]] = None
    team_members: Optional[List[str]] = None
    target_hires: Optional[int] = Field(default=None, ge=0)

    @field_validator("tags", "team_members", mode="before")
    @classmethod
    def _ensure_list(cls, value: Optional[Any]):
        """Allow comma-separated strings from forms for list fields."""
        if value is None or value == "":
            return None
        if isinstance(value, str):
            items = [item.strip() for item in value.split(",") if item.strip()]
            return items or None
        if isinstance(value, (set, tuple)):
            return list(value)
        return value

    @field_validator("status", "priority", mode="before")
    @classmethod
    def _normalize_choices(cls, value: Optional[str]):
        """Normalize choice strings to the expected lowercase slug format."""
        if value is None:
            return value
        normalized = value.strip().lower().replace(" ", "-").replace("_", "-")
        return normalized or None


class ProjectCreate(ProjectBase):
    pass


class ProjectRead(ProjectBase):
    project_id: str
    research_done: int
    research_status: Optional[str]
    created_by: str
    created_at: datetime
    tags: List[str] = Field(default_factory=list)
    team_members: List[str] = Field(default_factory=list)
    target_hires: int = 0
    hires_count: int = 0


class ProjectUpdate(ProjectBase):
    research_done: Optional[int] = None
    research_status: Optional[str] = None


class ProjectLifecycleUpdate(BaseModel):
    project_id: str
    status: Optional[str] = Field(default=None, pattern=r"^(active|on-hold|completed|archived)$")
    priority: Optional[str] = Field(default=None, pattern=r"^(urgent|high|medium|low)$")
    target_hires: Optional[int] = Field(default=None, ge=0)
    tags: Optional[List[str]] = None


class ProjectBulkLifecycleRequest(BaseModel):
    updates: List[ProjectLifecycleUpdate]
    cascade_positions: bool = False
    position_status: Optional[str] = Field(default=None, pattern=r"^(draft|open|closed)$")

class PositionBase(BaseModel):
    project_id: str
    title: str
    department: Optional[str] = None
    experience: Optional[str] = None
    responsibilities: Optional[List[str]] = None
    requirements: Optional[List[str]] = None
    location: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = Field(default="draft", pattern="^(draft|open|closed)$")
    openings: Optional[int] = Field(default=1, ge=0)


class PositionCreate(PositionBase):
    pass


class PositionRead(PositionBase):
    position_id: str
    created_at: datetime
    openings: int
    applicants_count: int


class PositionUpdate(BaseModel):
    title: Optional[str] = None
    department: Optional[str] = None
    experience: Optional[str] = None
    responsibilities: Optional[List[str]] = None
    requirements: Optional[List[str]] = None
    location: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = Field(default=None, pattern="^(draft|open|closed)$")
    openings: Optional[int] = Field(default=None, ge=0)


class CandidateBase(BaseModel):
    name: str
    project_id: Optional[str] = None
    position_id: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    source: str
    status: Optional[str] = Field(default="new", pattern="^(new|screening|interviewing|offer|hired|rejected|withdrawn)$")
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    resume_url: Optional[str] = None
    tags: Optional[List[str]] = None


class CandidateCreate(CandidateBase):
    pass


class CandidateRead(CandidateBase):
    candidate_id: str
    created_at: datetime
    ai_score: Optional[Any]


class CandidateUpdate(BaseModel):
    project_id: Optional[str] = None
    position_id: Optional[str] = None
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    source: Optional[str] = None
    status: Optional[str] = Field(default=None, pattern="^(new|screening|interviewing|offer|hired|rejected|withdrawn)$")
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    resume_url: Optional[str] = None
    ai_score: Optional[Any] = None
    tags: Optional[List[str]] = None


class CandidatePatch(BaseModel):
    status: Optional[str] = Field(default=None, pattern="^(new|screening|interviewing|offer|hired|rejected|withdrawn)$")
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    tags: Optional[List[str]] = None


class DocumentCreate(BaseModel):
    filename: str
    mime_type: str
    scope: str
    scope_id: Optional[str] = None


class DocumentRead(DocumentCreate):
    id: str
    file_url: str
    owner_user: Optional[str]
    uploaded_at: datetime


class ActivityRead(BaseModel):
    activity_id: str
    actor_type: str
    actor_id: Optional[str]
    project_id: Optional[str]
    position_id: Optional[str]
    candidate_id: Optional[str]
    event_type: str
    message: str
    created_at: datetime


class MarketResearchRequest(BaseModel):
    project_id: str
    region: str
    sector: Optional[str]
    summary: Optional[str]


class SalaryBenchmarkRequest(BaseModel):
    title: str
    region: str
    sector: Optional[str]
    seniority: Optional[str]


class SalaryBenchmarkResponse(BaseModel):
    currency: str
    annual_min: int
    annual_mid: int
    annual_max: int
    rationale: str
    sources: List[dict]


class OutreachRequest(BaseModel):
    title: str
    location: Optional[str]
    seniority: Optional[str]
    skills: List[str]
    candidate_name: str
    candidate_title: Optional[str]
    highlights: List[str] = []
    company: Optional[str]
    project_summary: Optional[str]


class OutreachResponse(BaseModel):
    subject: str
    body: str


class CallScriptRequest(BaseModel):
    title: str
    location: Optional[str]
    candidate_name: str
    value_props: List[str]


class CallScriptResponse(BaseModel):
    candidate: str
    role: str
    location: str
    value_props: List[str]
    sections: dict


class ChatbotMessageRequest(BaseModel):
    session_id: Optional[str] = None
    message: str


class ChatbotMessageResponse(BaseModel):
    session_id: str
    reply: str
    tools_suggested: List[str]
    context_echo: Optional[str] = None


class FileAnalysisRequest(BaseModel):
    document_id: str
    project_id: Optional[str] = None
    trigger_market_research: bool = True


class FileAnalysisResponse(BaseModel):
    project_info: dict
    positions: List[dict]
    file_diagnostics: dict
    document_type: str
    job_descriptions_generated: bool
    market_research_recommended: bool


class MarketResearchResponse(BaseModel):
    region: str
    sector: str
    summary: Optional[str]
    findings: List[dict]
    sources: List[dict]


class CandidateBulkActionRequest(BaseModel):
    action: str
    candidate_ids: List[str]
    tag: Optional[str] = None
    export_format: Optional[str] = Field(default="csv", pattern="^(csv|xlsx)$")


class CandidateBulkError(BaseModel):
    candidate_id: str
    error: str


class CandidateBulkActionResult(BaseModel):
    updated: Optional[int] = None
    deleted: Optional[int] = None
    message: Optional[str] = None
    success_count: Optional[int] = None
    failed_count: Optional[int] = None
    errors: Optional[List[CandidateBulkError]] = None


class SmartRecruitersJobImport(BaseModel):
    position_id: str
    job_url: Optional[AnyHttpUrl] = None
    job_id: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def _ensure_target(self) -> "SmartRecruitersJobImport":
        if not self.job_url and not self.job_id:
            raise ValueError("job_url or job_id must be provided")
        return self


class SmartRecruitersBulkRequest(BaseModel):
    project_id: str
    jobs: List[SmartRecruitersJobImport] = Field(default_factory=list)
    notes: Optional[str] = None
    default_filters: Optional[Dict[str, Any]] = None
    position_ids: Optional[List[str]] = None

    @model_validator(mode="after")
    def _populate_jobs(self) -> "SmartRecruitersBulkRequest":
        if self.position_ids and not self.jobs:
            raise ValueError(
                "jobs must be provided when using the deprecated position_ids field; "
                "include job_url or job_id for each position"
            )
        if not self.jobs:
            raise ValueError("At least one SmartRecruiters job must be provided")
        return self


class SourcingJobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: Optional[int]
    found_count: Optional[int]
    results: Optional[List[dict]]


class FeatureToggleRead(BaseModel):
    key: str
    value: Any
    overridden: bool = False
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None


class FeatureToggleUpdate(BaseModel):
    value: Any


class PromptPackRead(BaseModel):
    slug: str
    name: str
    category: str
    description: str
    tags: List[str]
    prompt: str


class EmbeddingIndexCreate(BaseModel):
    name: str
    description: Optional[str]
    vector_dim: int = Field(gt=0)
    location_uri: str


class EmbeddingIndexRead(EmbeddingIndexCreate):
    index_id: str
    created_by: Optional[str]
    created_at: datetime
