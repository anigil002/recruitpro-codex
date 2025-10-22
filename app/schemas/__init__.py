"""Pydantic schemas for API payloads."""

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str
    exp: int


class UserBase(BaseModel):
    email: EmailStr
    name: str
    role: str = Field(default="recruiter", regex="^(recruiter|admin)$")


class UserCreate(UserBase):
    password: str = Field(min_length=8)


class UserRead(UserBase):
    user_id: str
    created_at: datetime
    settings: Optional[dict]


class UserUpdate(BaseModel):
    name: Optional[str] = None


class UserSettingsUpdate(BaseModel):
    settings: dict


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


class ProjectCreate(ProjectBase):
    pass


class ProjectRead(ProjectBase):
    project_id: str
    research_done: int
    research_status: Optional[str]
    created_by: str
    created_at: datetime


class ProjectUpdate(ProjectBase):
    research_done: Optional[int] = None
    research_status: Optional[str] = None


class PositionBase(BaseModel):
    project_id: str
    title: str
    department: Optional[str] = None
    experience: Optional[str] = None
    responsibilities: Optional[List[str]] = None
    requirements: Optional[List[str]] = None
    location: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = Field(default="draft", regex="^(draft|open|closed)$")


class PositionCreate(PositionBase):
    pass


class PositionRead(PositionBase):
    position_id: str
    created_at: datetime


class PositionUpdate(BaseModel):
    title: Optional[str] = None
    department: Optional[str] = None
    experience: Optional[str] = None
    responsibilities: Optional[List[str]] = None
    requirements: Optional[List[str]] = None
    location: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = Field(default=None, regex="^(draft|open|closed)$")


class CandidateBase(BaseModel):
    name: str
    project_id: Optional[str] = None
    position_id: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    source: str
    status: Optional[str] = Field(default="new", regex="^(new|screening|interviewing|offer|hired|rejected|withdrawn)$")
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    resume_url: Optional[str] = None


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
    status: Optional[str] = Field(default=None, regex="^(new|screening|interviewing|offer|hired|rejected|withdrawn)$")
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    resume_url: Optional[str] = None
    ai_score: Optional[Any] = None


class CandidatePatch(BaseModel):
    status: Optional[str] = Field(default=None, regex="^(new|screening|interviewing|offer|hired|rejected|withdrawn)$")
    rating: Optional[int] = Field(default=None, ge=1, le=5)


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
    opening: str
    qualify: List[str]
    value_props: List[str]
    objections: List[dict]
    closing: str


class ChatbotMessageRequest(BaseModel):
    session_id: Optional[str] = None
    message: str


class ChatbotMessageResponse(BaseModel):
    session_id: str
    reply: str
    tools_suggested: List[str]
