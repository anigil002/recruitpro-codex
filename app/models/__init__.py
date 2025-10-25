"""SQLAlchemy models for the RecruitPro application."""

from datetime import datetime
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from ..database import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(String, primary_key=True)
    email = Column(String, nullable=False, unique=True)
    password_hash = Column(String, nullable=False)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    settings = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    projects = relationship("Project", back_populates="creator")


class Project(Base):
    __tablename__ = "projects"

    project_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    sector = Column(String)
    location_region = Column(String)
    summary = Column(Text)
    client = Column(String)
    status = Column(String, nullable=False, default="active")
    priority = Column(String, nullable=False, default="medium")
    department = Column(String)
    tags = Column(JSON, default=list)
    team_members = Column(JSON, default=list)
    target_hires = Column(Integer, nullable=False, default=0)
    hires_count = Column(Integer, nullable=False, default=0)
    research_done = Column(Integer, nullable=False, default=0)
    research_status = Column(String)
    created_by = Column(String, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    creator = relationship("User", back_populates="projects")
    positions = relationship("Position", back_populates="project", cascade="all, delete")
    documents = relationship("ProjectDocument", back_populates="project", cascade="all, delete")


class ProjectDocument(Base):
    __tablename__ = "project_documents"

    doc_id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False)
    filename = Column(String, nullable=False)
    file_url = Column(String, nullable=False)
    mime_type = Column(String, nullable=False)
    uploaded_by = Column(String, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="documents")


class Position(Base):
    __tablename__ = "positions"

    position_id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    department = Column(String)
    experience = Column(String)
    responsibilities = Column(JSON)
    requirements = Column(JSON)
    location = Column(String)
    description = Column(Text)
    status = Column(String, nullable=False, default="draft")
    openings = Column(Integer, nullable=False, default=1)
    applicants_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("project_id", "title", "location", name="ux_positions_project_title_loc"),
    )

    project = relationship("Project", back_populates="positions")
    candidates = relationship("Candidate", back_populates="position")


class Candidate(Base):
    __tablename__ = "candidates"

    candidate_id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.project_id", ondelete="SET NULL"))
    position_id = Column(String, ForeignKey("positions.position_id", ondelete="SET NULL"))
    name = Column(String, nullable=False)
    email = Column(String)
    phone = Column(String)
    source = Column(String, nullable=False)
    status = Column(String, nullable=False, default="new")
    rating = Column(Integer)
    resume_url = Column(String)
    tags = Column(JSON)
    ai_score = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    project = relationship("Project")
    position = relationship("Position", back_populates="candidates")


class CandidateStatusHistory(Base):
    __tablename__ = "candidate_status_history"

    history_id = Column(String, primary_key=True)
    candidate_id = Column(String, ForeignKey("candidates.candidate_id", ondelete="CASCADE"), nullable=False)
    old_status = Column(String)
    new_status = Column(String, nullable=False)
    changed_by = Column(String, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=False)
    changed_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AIJob(Base):
    __tablename__ = "ai_jobs"

    job_id = Column(String, primary_key=True)
    job_type = Column(String, nullable=False)
    project_id = Column(String, ForeignKey("projects.project_id", ondelete="CASCADE"))
    position_id = Column(String, ForeignKey("positions.position_id", ondelete="CASCADE"))
    candidate_id = Column(String, ForeignKey("candidates.candidate_id", ondelete="CASCADE"))
    status = Column(String, nullable=False, default="pending")
    request_json = Column(JSON)
    response_json = Column(JSON)
    error = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime)


class SourcingJob(Base):
    __tablename__ = "sourcing_jobs"

    sourcing_job_id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False)
    position_id = Column(String, ForeignKey("positions.position_id", ondelete="CASCADE"), nullable=False)
    params_json = Column(JSON, nullable=False)
    status = Column(String, nullable=False, default="pending")
    progress = Column(Integer, nullable=False, default=0)
    found_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime)


class SourcingResult(Base):
    __tablename__ = "sourcing_results"

    result_id = Column(String, primary_key=True)
    sourcing_job_id = Column(String, ForeignKey("sourcing_jobs.sourcing_job_id", ondelete="CASCADE"), nullable=False)
    platform = Column(String, nullable=False)
    profile_url = Column(String, nullable=False)
    name = Column(String)
    title = Column(String)
    company = Column(String)
    location = Column(String)
    summary = Column(Text)
    quality_score = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("sourcing_job_id", "profile_url", name="ux_src_results_profile_per_job"),
    )


class ScreeningRun(Base):
    __tablename__ = "screening_runs"

    screening_id = Column(String, primary_key=True)
    candidate_id = Column(String, ForeignKey("candidates.candidate_id", ondelete="CASCADE"), nullable=False)
    position_id = Column(String, ForeignKey("positions.position_id", ondelete="CASCADE"), nullable=False)
    score_json = Column(JSON, nullable=False)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ProjectMarketResearch(Base):
    __tablename__ = "project_market_research"

    research_id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False)
    region = Column(String, nullable=False)
    window = Column(String, nullable=False)
    findings = Column(JSON, nullable=False)
    sources = Column(JSON, nullable=False)
    status = Column(String, nullable=False, default="completed")
    error = Column(Text)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime)


class Interview(Base):
    __tablename__ = "interviews"

    interview_id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.project_id", ondelete="SET NULL"))
    position_id = Column(String, ForeignKey("positions.position_id", ondelete="CASCADE"), nullable=False)
    candidate_id = Column(String, ForeignKey("candidates.candidate_id", ondelete="CASCADE"), nullable=False)
    scheduled_at = Column(DateTime, nullable=False)
    location = Column(String)
    mode = Column(String)
    notes = Column(Text)
    feedback = Column(Text)
    updated_by = Column(String, ForeignKey("users.user_id", ondelete="SET NULL"))
    updated_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ActivityFeed(Base):
    __tablename__ = "activity_feed"

    activity_id = Column(String, primary_key=True)
    actor_type = Column(String, nullable=False)
    actor_id = Column(String)
    project_id = Column(String, ForeignKey("projects.project_id", ondelete="SET NULL"))
    position_id = Column(String, ForeignKey("positions.position_id", ondelete="SET NULL"))
    candidate_id = Column(String, ForeignKey("candidates.candidate_id", ondelete="SET NULL"))
    event_type = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True)
    filename = Column(String, nullable=False)
    file_url = Column(String, nullable=False)
    mime_type = Column(String, nullable=False)
    owner_user = Column(String, ForeignKey("users.user_id", ondelete="SET NULL"))
    scope = Column(String, nullable=False)
    scope_id = Column(String)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ChatbotSession(Base):
    __tablename__ = "chatbot_sessions"

    session_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    context_json = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime)


class ChatbotMessage(Base):
    __tablename__ = "chatbot_messages"

    message_id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey("chatbot_sessions.session_id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class CommunicationTemplate(Base):
    __tablename__ = "communication_templates"

    template_id = Column(String, primary_key=True)
    type = Column(String, nullable=False)
    name = Column(String, nullable=False)
    template_json = Column(JSON, nullable=False)
    created_by = Column(String, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class OutreachRun(Base):
    __tablename__ = "outreach_runs"

    outreach_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=False)
    candidate_id = Column(String, ForeignKey("candidates.candidate_id", ondelete="SET NULL"))
    position_id = Column(String, ForeignKey("positions.position_id", ondelete="SET NULL"))
    type = Column(String, nullable=False)
    output_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class SalaryBenchmark(Base):
    __tablename__ = "salary_benchmarks"

    benchmark_id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    region = Column(String, nullable=False)
    sector = Column(String)
    seniority = Column(String)
    currency = Column(String, nullable=False)
    annual_min = Column(Integer, nullable=False)
    annual_mid = Column(Integer, nullable=False)
    annual_max = Column(Integer, nullable=False)
    rationale = Column(Text)
    sources = Column(JSON, nullable=False)
    created_by = Column(String, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AdvancedFeaturesConfig(Base):
    __tablename__ = "advanced_features_config"

    key = Column(String, primary_key=True)
    value_json = Column(JSON, nullable=False)
    updated_by = Column(String, ForeignKey("users.user_id", ondelete="SET NULL"))
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class IntegrationCredential(Base):
    __tablename__ = "integration_credentials"

    key = Column(String, primary_key=True)
    value_encrypted = Column(Text, nullable=False)
    updated_by = Column(String, ForeignKey("users.user_id", ondelete="SET NULL"))
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class EmbeddingIndexRef(Base):
    __tablename__ = "embeddings_index_refs"

    index_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    vector_dim = Column(Integer, nullable=False)
    location_uri = Column(String, nullable=False)
    created_by = Column(String, ForeignKey("users.user_id", ondelete="SET NULL"))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AdminMigrationLog(Base):
    __tablename__ = "admin_migration_logs"

    migration_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=False)
    source_name = Column(String, nullable=False)
    items_total = Column(Integer, nullable=False)
    items_success = Column(Integer, nullable=False)
    items_failed = Column(Integer, nullable=False)
    error_json = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
