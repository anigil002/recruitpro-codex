# RecruitPro - System Architecture Document

**Version:** 1.0
**Date:** November 25, 2025
**Status:** Approved
**Author:** RecruitPro Architecture Team

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architectural Overview](#architectural-overview)
3. [System Context](#system-context)
4. [Container Architecture](#container-architecture)
5. [Component Architecture](#component-architecture)
6. [Data Architecture](#data-architecture)
7. [Integration Architecture](#integration-architecture)
8. [Deployment Architecture](#deployment-architecture)
9. [Security Architecture](#security-architecture)
10. [Technology Stack](#technology-stack)
11. [Design Patterns](#design-patterns)
12. [Scalability and Performance](#scalability-and-performance)
13. [Disaster Recovery](#disaster-recovery)

---

## Executive Summary

RecruitPro is a modern, AI-powered Applicant Tracking System built on a three-tier architecture:

1. **Presentation Layer**: Jinja2 templates with Tailwind CSS, Electron desktop app
2. **Application Layer**: FastAPI REST API with async support
3. **Data Layer**: PostgreSQL/SQLite with SQLAlchemy ORM

The system follows microservices principles with clear separation of concerns, stateless authentication, and horizontal scalability. It integrates with Google Gemini for AI capabilities and supports both web and desktop deployments.

### Key Architectural Decisions

- **Stateless Architecture**: JWT-based authentication enables horizontal scaling
- **API-First Design**: All functionality exposed via REST API
- **Graceful Degradation**: System remains functional when external services fail
- **Background Processing**: Queue-based async processing for long-running tasks
- **Multi-Tenancy Ready**: Single-tenant initially, architecture supports multi-tenancy

---

## Architectural Overview

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                             │
├─────────────────────────────────────────────────────────────────┤
│  Web Browser          │  Electron Desktop App    │  Mobile (Future)
│  (Chrome, Firefox,    │  (Windows, macOS, Linux) │  (iOS, Android)
│   Safari, Edge)       │                          │
└──────────┬────────────┴──────────┬───────────────┴──────────────┘
           │                       │
           │ HTTPS/TLS            │ Local HTTP
           │                       │
┌──────────▼────────────────────────▼──────────────────────────────┐
│                     PRESENTATION LAYER                           │
├──────────────────────────────────────────────────────────────────┤
│  Nginx Reverse Proxy (Production)                                │
│  ├─ HTTPS Termination                                            │
│  ├─ Rate Limiting                                                │
│  ├─ Static File Serving (/storage/*)                             │
│  └─ Load Balancing (Multi-Instance)                              │
└──────────┬───────────────────────────────────────────────────────┘
           │
           │ HTTP/HTTPS
           │
┌──────────▼───────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                             │
├──────────────────────────────────────────────────────────────────┤
│  FastAPI Application (Uvicorn ASGI Server)                       │
│  ├─ Routers (API Endpoints)                                      │
│  ├─ Services (Business Logic)                                    │
│  ├─ Background Queue (Redis+RQ or In-Memory)                     │
│  ├─ Middleware (CORS, Security, Rate Limiting)                   │
│  └─ Dependency Injection (Auth, DB Sessions)                     │
└──────────┬───────────────────┬───────────────────────────────────┘
           │                   │
           │                   │ Background Jobs
           │                   │
           │          ┌────────▼────────┐
           │          │  Redis Queue    │
           │          │  (RQ Workers)   │
           │          └────────┬────────┘
           │                   │
           │                   │ Job Processing
           │                   │
┌──────────▼───────────────────▼───────────────────────────────────┐
│                       SERVICE LAYER                              │
├──────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────────┐ │
│  │  Gemini AI  │  │  Sourcing    │  │  Storage & Document     │ │
│  │  Service    │  │  Service     │  │  Service                │ │
│  └─────────────┘  └──────────────┘  └─────────────────────────┘ │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────────┐ │
│  │  Events &   │  │  Security &  │  │  Email & Notification   │ │
│  │  Activity   │  │  Encryption  │  │  Service (Future)       │ │
│  └─────────────┘  └──────────────┘  └─────────────────────────┘ │
└──────────┬───────────────────────────────────────────────────────┘
           │
           │ SQLAlchemy ORM
           │
┌──────────▼───────────────────────────────────────────────────────┐
│                        DATA LAYER                                │
├──────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌──────────────┐  ┌───────────────────┐   │
│  │  PostgreSQL     │  │  Redis       │  │  File Storage     │   │
│  │  (Production)   │  │  (Cache &    │  │  (Local/S3)       │   │
│  │                 │  │   Queue)     │  │                   │   │
│  │  - Projects     │  └──────────────┘  │  - Resumes/CVs    │   │
│  │  - Candidates   │                    │  - Documents      │   │
│  │  - Positions    │                    │  - Uploads        │   │
│  │  - Users        │                    └───────────────────┘   │
│  │  - Activity     │                                            │
│  └─────────────────┘                                            │
│                                                                  │
│  ┌─────────────────┐                                            │
│  │  SQLite         │                                            │
│  │  (Development)  │                                            │
│  └─────────────────┘                                            │
└──────────┬───────────────────────────────────────────────────────┘
           │
           │ External API Calls (HTTPS)
           │
┌──────────▼───────────────────────────────────────────────────────┐
│                  EXTERNAL INTEGRATIONS                           │
├──────────────────────────────────────────────────────────────────┤
│  ┌────────────────┐  ┌──────────────────┐  ┌─────────────────┐  │
│  │  Google Gemini │  │  Google Custom   │  │ SmartRecruiters │  │
│  │  API           │  │  Search API      │  │ (Web Scraping)  │  │
│  │  (AI Engine)   │  │  (LinkedIn XRay) │  │                 │  │
│  └────────────────┘  └──────────────────┘  └─────────────────┘  │
│                                                                  │
│  ┌────────────────┐  ┌──────────────────┐  ┌─────────────────┐  │
│  │  Sentry        │  │  Prometheus      │  │  Future APIs    │  │
│  │  (Monitoring)  │  │  (Metrics)       │  │  (Email, Cal)   │  │
│  └────────────────┘  └──────────────────┘  └─────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### Architectural Principles

1. **Separation of Concerns**: Clear boundaries between presentation, business logic, and data
2. **Loose Coupling**: Components interact via well-defined interfaces
3. **High Cohesion**: Related functionality grouped together
4. **Stateless Design**: No server-side sessions, JWT-based auth
5. **Fail-Safe**: Graceful degradation when external services unavailable
6. **Testability**: Dependency injection enables unit and integration testing
7. **Scalability**: Horizontal scaling via stateless architecture
8. **Security-First**: Defense in depth, least privilege, encryption

---

## System Context

### System Context Diagram (C4 Model Level 1)

```
                    ┌─────────────────┐
                    │   Recruiter     │
                    │   (User)        │
                    └────────┬────────┘
                             │
                             │ Uses
                             │
          ┌──────────────────▼─────────────────────┐
          │                                        │
          │         RecruitPro ATS                 │
          │                                        │
          │  AI-powered recruitment platform       │
          │  for candidate management, sourcing,   │
          │  screening, and market intelligence    │
          │                                        │
          └──┬─────────────┬──────────────┬────────┘
             │             │              │
             │ Screens CVs │ Sources      │ Stores
             │ Generates   │ Candidates   │ Files
             │ Insights    │              │
             │             │              │
   ┌─────────▼────────┐ ┌──▼────────────┐ ┌▼────────────┐
   │  Google Gemini   │ │  LinkedIn     │ │  File       │
   │  AI API          │ │  (via Google  │ │  Storage    │
   │                  │ │   Search)     │ │  (Local/S3) │
   │  - CV Screening  │ │               │ │             │
   │  - JD Generation │ │ SmartRecruiters│ │             │
   │  - Market        │ │  Platform     │ │             │
   │    Research      │ │  (Automation) │ │             │
   └──────────────────┘ └───────────────┘ └─────────────┘
```

### External Actors

| Actor | Description | Interaction |
|-------|-------------|-------------|
| **Recruiter** | Primary user managing recruitment projects | Web/Desktop UI |
| **Admin** | Workspace administrator configuring integrations | Web UI (Settings) |
| **Candidate** | Passive participant (data subject) | None (future: candidate portal) |
| **System Cron** | Scheduled tasks (backups, cleanup) | CLI scripts |

### External Systems

| System | Purpose | Protocol | Criticality |
|--------|---------|----------|-------------|
| **Google Gemini API** | AI-powered screening, insights | HTTPS/REST | High (with fallback) |
| **Google Custom Search** | LinkedIn candidate sourcing | HTTPS/REST | Medium |
| **SmartRecruiters** | Candidate import | Web Scraping (Playwright) | Low |
| **Sentry** | Error tracking & monitoring | HTTPS | Low |
| **Prometheus** | Metrics & observability | HTTP | Low |

---

## Container Architecture

### Container Diagram (C4 Model Level 2)

```
┌────────────────────────────────────────────────────────────────┐
│                        Web Browser                             │
│  (React/JavaScript - Future) OR Jinja2 Templates              │
│  - Login/Registration Forms                                    │
│  - Dashboard (Projects, Candidates, Positions)                 │
│  - CV Screening Results                                        │
│  - Settings & Configuration                                    │
└──────────────────────────┬─────────────────────────────────────┘
                           │
                           │ HTTPS (JSON/HTML)
                           │
┌──────────────────────────▼─────────────────────────────────────┐
│                  FastAPI Application                           │
│  (Python 3.11+, Uvicorn)                                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  API Layer (app/routers/)                                │  │
│  │  - Authentication (/api/auth/*)                          │  │
│  │  - Projects (/api/projects/*)                            │  │
│  │  - Candidates (/api/candidates/*)                        │  │
│  │  - AI Features (/api/ai/*)                               │  │
│  │  - Sourcing (/api/sourcing/*)                            │  │
│  │  - Admin (/api/admin/*)                                  │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Service Layer (app/services/)                           │  │
│  │  - Gemini AI Service (CV screening, JD gen, research)    │  │
│  │  - Sourcing Service (LinkedIn, SmartRecruiters)          │  │
│  │  - Storage Service (File upload/download)                │  │
│  │  - Event Service (Activity logging)                      │  │
│  │  - Security Service (Auth, encryption)                   │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Data Access Layer (app/models/, app/database.py)       │  │
│  │  - SQLAlchemy ORM Models                                 │  │
│  │  - Database Session Management                           │  │
│  │  - Repository Pattern                                    │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────┬──────────────────┬──────────────────┬─────────────────┘
         │                  │                  │
         │                  │                  │
         │                  │                  │
┌────────▼────────┐ ┌───────▼────────┐ ┌──────▼───────────────┐
│  PostgreSQL     │ │  Redis         │ │  File Storage        │
│  Database       │ │  (Queue/Cache) │ │  (Local/S3)          │
│                 │ │                │ │                      │
│  - 15+ Tables   │ │  - RQ Jobs     │ │  - /storage/         │
│  - Indexes      │ │  - Session     │ │    projects/         │
│  - Constraints  │ │    Cache       │ │    candidates/       │
│                 │ │  - Pub/Sub     │ │    documents/        │
└─────────────────┘ └────────────────┘ └──────────────────────┘
```

### Container Responsibilities

#### 1. **Web Application (Frontend)**

**Technology**: HTML5, Jinja2, Tailwind CSS, JavaScript ES6+
**Deployment**: Served by FastAPI static file handler
**Responsibilities**:
- User interface rendering
- Form validation (client-side)
- AJAX API calls
- Token management (localStorage)
- Real-time updates (SSE)

**Key Files**:
- `templates/recruitpro_ats.html` - Main dashboard
- `templates/login.html` - Authentication
- `templates/candidate_profile.html` - Candidate details
- `static/css/output.css` - Tailwind compiled styles
- `static/js/` - JavaScript modules

#### 2. **API Application (Backend)**

**Technology**: Python 3.11+, FastAPI 0.111.0+, Uvicorn
**Deployment**: Systemd service or Docker container
**Responsibilities**:
- REST API endpoints
- Business logic execution
- Authentication & authorization
- Input validation (Pydantic)
- Background job queuing
- Activity logging

**Key Modules**:
- `app/main.py` - Application factory
- `app/routers/` - API route handlers (13 routers)
- `app/services/` - Business logic services
- `app/models/` - SQLAlchemy ORM models
- `app/utils/` - Shared utilities

#### 3. **Database (PostgreSQL/SQLite)**

**Technology**: PostgreSQL 14+ (production), SQLite 3.x (development)
**Deployment**: Managed service (RDS, Cloud SQL) or self-hosted
**Responsibilities**:
- Persistent data storage
- Transaction management
- Data integrity (constraints, indexes)
- Full-text search (PostgreSQL)

**Schema**:
- 15+ tables
- 50+ indexes
- Foreign key constraints
- JSONB columns for flexible data

#### 4. **Cache & Queue (Redis)**

**Technology**: Redis 5.0+, RQ (Redis Queue) 1.16.0+
**Deployment**: Managed service or self-hosted
**Responsibilities**:
- Background job queue
- Session caching (future)
- Pub/Sub for real-time events
- Rate limiting data

**Queues**:
- `default` - General background jobs
- `high` - User-initiated AI requests
- `low` - Scheduled maintenance tasks

#### 5. **File Storage**

**Technology**: Local filesystem (development), S3-compatible (production)
**Deployment**: Local directory or cloud object storage
**Responsibilities**:
- Resume/CV storage
- Project document storage
- User uploads
- Temporary files

**Structure**:
```
/storage/
  ├── projects/{project_id}/
  ├── candidates/{candidate_id}/
  ├── documents/{document_id}/
  └── temp/
```

---

## Component Architecture

### Component Diagram (C4 Model Level 3) - API Application

```
┌───────────────────────────────────────────────────────────────────┐
│                     FastAPI Application                           │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    Middleware Stack                         │ │
│  ├─────────────────────────────────────────────────────────────┤ │
│  │  1. SecurityHeadersMiddleware (HSTS, CSP, X-Frame-Options) │ │
│  │  2. HTTPSRedirectMiddleware (Production only)              │ │
│  │  3. CORSMiddleware (Cross-origin requests)                 │ │
│  │  4. TrustedHostMiddleware (Host header validation)         │ │
│  │  5. RateLimitMiddleware (SlowAPI - 100 req/min)            │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    Routers (API Endpoints)                  │ │
│  ├─────────────────────────────────────────────────────────────┤ │
│  │  AuthRouter         (/api/auth/*)                          │ │
│  │  ProjectsRouter     (/api/projects/*)                       │ │
│  │  PositionsRouter    (/api/positions/*)                      │ │
│  │  CandidatesRouter   (/api/candidates/*)                     │ │
│  │  AIRouter           (/api/ai/*)                             │ │
│  │  ResearchRouter     (/api/research/*)                       │ │
│  │  SourcingRouter     (/api/sourcing/*)                       │ │
│  │  DocumentsRouter    (/api/documents/*)                      │ │
│  │  InterviewsRouter   (/api/interviews/*)                     │ │
│  │  ActivityRouter     (/api/activity/*)                       │ │
│  │  AdminRouter        (/api/admin/*)                          │ │
│  │  SettingsRouter     (/api/settings/*)                       │ │
│  │  SystemRouter       (/api/health, /api/version)             │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                              │                                    │
│                              │ Depends on                         │
│                              ▼                                    │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              Dependency Injection (app/deps.py)             │ │
│  ├─────────────────────────────────────────────────────────────┤ │
│  │  get_db()              → Database session                   │ │
│  │  get_current_user()    → Authenticated user                 │ │
│  │  require_admin()       → Admin authorization                │ │
│  │  get_background_queue()→ Background queue instance          │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                              │                                    │
│                              │ Uses                               │
│                              ▼                                    │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                  Services (Business Logic)                  │ │
│  ├─────────────────────────────────────────────────────────────┤ │
│  │  ┌───────────────┐  ┌────────────────┐  ┌───────────────┐ │ │
│  │  │ GeminiService │  │SourcingService │  │StorageService │ │ │
│  │  ├───────────────┤  ├────────────────┤  ├───────────────┤ │ │
│  │  │screen_cv()    │  │linkedin_xray() │  │save_file()    │ │ │
│  │  │analyze_file() │  │smartrecruiters│  │delete_file()  │ │ │
│  │  │generate_jd()  │  │  _scrape()     │  │get_file()     │ │ │
│  │  │market_research│  └────────────────┘  └───────────────┘ │ │
│  │  │salary_bench() │                                         │ │
│  │  │chatbot_reply()│  ┌────────────────┐  ┌───────────────┐ │ │
│  │  └───────────────┘  │ EventService   │  │SecurityService│ │ │
│  │                     ├────────────────┤  ├───────────────┤ │ │
│  │  ┌───────────────┐  │log_activity()  │  │hash_password()│ │ │
│  │  │ AIService     │  │publish_sync()  │  │verify_pass()  │ │ │
│  │  ├───────────────┤  │publish_async() │  │create_token() │ │ │
│  │  │enqueue_job()  │  └────────────────┘  │decrypt()      │ │ │
│  │  │handle_job()   │                      │encrypt()      │ │ │
│  │  │get_job_status│  ┌────────────────┐  └───────────────┘ │ │
│  │  └───────────────┘  │ QueueService   │                    │ │
│  │                     ├────────────────┤                    │ │
│  │                     │enqueue()       │                    │ │
│  │                     │worker_loop()   │                    │ │
│  │                     │get_stats()     │                    │ │
│  │                     └────────────────┘                    │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                              │                                    │
│                              │ Uses                               │
│                              ▼                                    │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │               Models (Data Access Layer)                    │ │
│  ├─────────────────────────────────────────────────────────────┤ │
│  │  User, Project, Position, Candidate, Interview,             │ │
│  │  Document, ActivityFeed, AIJob, ScreeningRun,               │ │
│  │  SourcingJob, SourcingResult, SalaryBenchmark, etc.         │ │
│  │                                                             │ │
│  │  Each model extends SQLAlchemy Base with:                   │ │
│  │  - Table definition (__tablename__)                         │ │
│  │  - Columns (mapped to database fields)                      │ │
│  │  - Relationships (foreign keys, joins)                      │ │
│  │  - Methods (business logic, validations)                    │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                              │                                    │
│                              │ SQLAlchemy ORM                     │
│                              ▼                                    │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              Database Session Management                    │ │
│  ├─────────────────────────────────────────────────────────────┤ │
│  │  SessionLocal (scoped_session)                              │ │
│  │  - Connection pooling (pool_size=20, max_overflow=30)       │ │
│  │  - Transaction management (commit/rollback)                 │ │
│  │  - Context manager support (with statement)                 │ │
│  └─────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────┘
```

### Component Descriptions

#### **Routers (app/routers/)**

Lightweight controllers that:
- Parse HTTP requests
- Validate input via Pydantic schemas
- Call service layer methods
- Format responses
- Handle HTTP errors

**Example** (`app/routers/candidates.py`):
```python
@router.post("/", response_model=CandidateResponse)
async def create_candidate(
    candidate: CandidateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new candidate"""
    # Validation handled by Pydantic
    # Business logic in service layer
    return candidate_service.create(db, candidate, current_user)
```

#### **Services (app/services/)**

Business logic layer that:
- Implements core functionality
- Orchestrates multiple models
- Handles external API calls
- Manages transactions
- Enforces business rules

**Example** (`app/services/gemini.py`):
```python
def screen_cv(cv_text: str, position_requirements: dict) -> dict:
    """Screen CV against position requirements"""
    # 1. Build AI prompt
    # 2. Call Gemini API
    # 3. Parse structured response
    # 4. Apply business rules
    # 5. Return screening result
```

#### **Models (app/models/)**

Data access layer that:
- Defines database schema
- Maps Python objects to tables
- Implements relationships
- Provides query methods
- Validates data constraints

**Example** (`app/models/candidate.py`):
```python
class Candidate(Base):
    __tablename__ = "candidates"

    candidate_id = Column(String, primary_key=True)
    email = Column(String, nullable=False)
    status = Column(Enum(CandidateStatus), default="new")

    # Relationships
    project = relationship("Project", back_populates="candidates")
    screening_runs = relationship("ScreeningRun", back_populates="candidate")
```

#### **Utilities (app/utils/)**

Cross-cutting concerns:
- **security.py**: Password hashing, JWT tokens, RBAC
- **exceptions.py**: Custom exception classes
- **secrets.py**: Encryption/decryption
- **storage.py**: File handling
- **validators.py**: Input validation helpers

---

## Data Architecture

### Entity-Relationship Diagram

```
┌──────────────────┐          ┌──────────────────┐
│      users       │          │     projects     │
├──────────────────┤          ├──────────────────┤
│ user_id (PK)     │◄────────┬│ project_id (PK)  │
│ email (UNIQUE)   │         ││ created_by (FK)  │
│ password_hash    │         ││ name             │
│ role             │         ││ client           │
│ settings (JSON)  │         ││ status           │
└──────────────────┘         │└──────────────────┘
                             │         │
                             │         │ 1:N
                             │         ▼
                             │┌──────────────────┐
                             ││    positions     │
                             │├──────────────────┤
                             ││ position_id (PK) │
                             ││ project_id (FK)  │
                             ││ title            │
                             ││ requirements(JSON)│
                             │└──────────────────┘
                             │         │
                             │         │ 1:N
                             │         ▼
                             │┌──────────────────┐
                             ││   candidates     │
                             │├──────────────────┤
                             └│ candidate_id (PK)│
                              │ created_by (FK)  │
                              │ project_id (FK)  │
                              │ position_id (FK) │
                              │ status           │
                              │ ai_score (JSON)  │
                              └──────────────────┘
                                       │
                              ┌────────┴────────┐
                              │ 1:N             │ 1:N
                              ▼                 ▼
                     ┌──────────────────┐ ┌──────────────────┐
                     │ screening_runs   │ │candidate_status_ │
                     │                  │ │    history       │
                     ├──────────────────┤ ├──────────────────┤
                     │ screening_id(PK) │ │ history_id (PK)  │
                     │ candidate_id(FK) │ │ candidate_id(FK) │
                     │ position_id (FK) │ │ old_status       │
                     │ overall_fit      │ │ new_status       │
                     │ final_decision   │ │ changed_by (FK)  │
                     └──────────────────┘ └──────────────────┘
```

### Data Flow Patterns

#### 1. **Read Pattern** (Query)

```
Client Request
     │
     ▼
Router (Pydantic validation)
     │
     ▼
Service Layer (Business logic)
     │
     ▼
Model/Repository (ORM query)
     │
     ▼
Database (SELECT)
     │
     ▼
Model Instance (Python object)
     │
     ▼
Service Layer (Post-processing)
     │
     ▼
Pydantic Schema (Response serialization)
     │
     ▼
JSON Response
```

#### 2. **Write Pattern** (Create/Update)

```
Client Request (JSON)
     │
     ▼
Router (Pydantic schema validation)
     │
     ▼
Service Layer
     ├─ Business rule validation
     ├─ Authorization check
     └─ Start transaction
            │
            ▼
       Model Create/Update
            │
            ▼
       Database (INSERT/UPDATE)
            │
            ▼
       Activity Logging (async)
            │
            ▼
       Commit Transaction
            │
            ▼
       Response (JSON)
```

#### 3. **Background Job Pattern**

```
Client Request (AI Screening)
     │
     ▼
Router
     │
     ▼
Service Layer
     ├─ Create AIJob record (status=pending)
     ├─ Enqueue job to background queue
     └─ Return job_id immediately
            │
            ▼
       Background Worker
            ├─ Dequeue job
            ├─ Update status=running
            ├─ Execute job (Gemini API call)
            ├─ Update status=completed/failed
            ├─ Store response_json
            └─ Publish real-time event
                   │
                   ▼
              Client polls or receives SSE update
```

### Data Storage Strategy

| Data Type | Storage | Rationale |
|-----------|---------|-----------|
| **Structured Data** | PostgreSQL | ACID compliance, complex queries, relationships |
| **User Uploads** | Filesystem/S3 | Cost-effective, CDN-friendly |
| **Session Cache** | Redis | Fast access, expiration support |
| **Background Jobs** | Redis (RQ) | Reliable queue, job persistence |
| **Activity Logs** | PostgreSQL | Audit trail, searchable |
| **AI Results** | PostgreSQL (JSONB) | Flexible schema, queryable |

---

## Integration Architecture

### Integration Patterns

#### 1. **Synchronous API Calls** (Gemini, Google Search)

```
RecruitPro
     │
     │ HTTP POST (JSON)
     ▼
Google Gemini API
     │
     │ Response (JSON)
     ▼
Parse & Store
```

**Error Handling**:
- Timeout: 30 seconds
- Retry: Exponential backoff (2s, 4s, 8s, 16s)
- Fallback: Heuristic-based logic

#### 2. **Web Scraping** (SmartRecruiters)

```
RecruitPro
     │
     │ Playwright Browser Automation
     ▼
SmartRecruiters Web UI
     │
     │ HTML Response
     ▼
Parse & Extract Data
     │
     ▼
Store in Database
```

**Error Handling**:
- Login failure → SmartRecruitersLoginError
- CAPTCHA detection → Manual intervention required
- Rate limiting → Exponential backoff

#### 3. **Server-Sent Events** (Real-time Updates)

```
Client (Browser)
     │
     │ EventSource connection
     ▼
RecruitPro /api/activity/stream
     │
     │ Keep-alive, push events
     ▼
Client updates UI in real-time
```

### Integration Security

| Integration | Auth Method | Encryption | Rate Limit |
|-------------|-------------|------------|------------|
| **Gemini API** | API Key (header) | TLS 1.2+ | As per Google terms |
| **Google CSE** | API Key (query param) | TLS 1.2+ | 100/day (free tier) |
| **SmartRecruiters** | Session cookies | TLS 1.2+ | Respectful delays |
| **Sentry** | DSN token | TLS 1.2+ | N/A |

---

## Deployment Architecture

### Development Environment

```
┌─────────────────────────────────────────┐
│     Developer Workstation               │
├─────────────────────────────────────────┤
│  Python 3.11 Virtual Environment        │
│  ├─ FastAPI (Uvicorn, port 8000)        │
│  ├─ SQLite Database (./data/)           │
│  ├─ In-memory background queue          │
│  └─ Local file storage (./storage/)     │
│                                         │
│  Node.js (Tailwind CSS build)           │
│  └─ npm run build:css (watch mode)      │
└─────────────────────────────────────────┘
```

**Setup**:
```bash
python -m venv venv
source venv/bin/activate
pip install -e .[dev]
python -m app.database  # Initialize DB
uvicorn app.main:app --reload
```

### Production Environment (Single Server)

```
┌───────────────────────────────────────────────────────────┐
│                    Production Server                      │
├───────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  Nginx (Port 80/443)                                │ │
│  │  ├─ HTTPS Termination (Let's Encrypt)               │ │
│  │  ├─ Static Files (/storage/*)                       │ │
│  │  └─ Reverse Proxy → Uvicorn (localhost:8000)        │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  Systemd Services                                   │ │
│  │  ├─ recruitpro-web.service (Uvicorn)                │ │
│  │  ├─ recruitpro-worker.service (RQ worker)           │ │
│  │  ├─ postgresql.service                              │ │
│  │  └─ redis.service                                   │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  PostgreSQL (Port 5432, localhost only)             │ │
│  │  - Database: recruitpro                             │ │
│  │  - User: recruitpro                                 │ │
│  │  - Connection pool: 20 connections                  │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  Redis (Port 6379, localhost only)                  │ │
│  │  - Persistence: AOF + RDB                           │ │
│  │  - Max memory: 256MB                                │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  File Storage (/var/lib/recruitpro/storage/)        │ │
│  │  - Owner: recruitpro user                           │ │
│  │  - Permissions: 750                                 │ │
│  └─────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────┘
```

### Production Environment (Multi-Server with Load Balancer)

```
                    ┌──────────────────┐
                    │  Load Balancer   │
                    │  (Nginx/HAProxy) │
                    └────────┬─────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
              ▼                             ▼
     ┌─────────────────┐           ┌─────────────────┐
     │  App Server 1   │           │  App Server 2   │
     ├─────────────────┤           ├─────────────────┤
     │ Uvicorn (8000)  │           │ Uvicorn (8000)  │
     │ RQ Worker       │           │ RQ Worker       │
     └────────┬────────┘           └────────┬────────┘
              │                             │
              └──────────────┬──────────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
              ▼                             ▼
     ┌─────────────────┐           ┌─────────────────┐
     │  PostgreSQL     │           │  Redis          │
     │  (Master-Slave) │           │  (Cluster)      │
     └─────────────────┘           └─────────────────┘
              │
              ▼
     ┌─────────────────┐
     │  S3 Storage     │
     │  (CloudFront)   │
     └─────────────────┘
```

### Containerized Deployment (Docker)

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - RECRUITPRO_DATABASE_URL=postgresql://user:pass@db:5432/recruitpro
      - RECRUITPRO_REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - ./storage:/app/storage

  worker:
    build: .
    command: rq worker
    environment:
      - RECRUITPRO_DATABASE_URL=postgresql://user:pass@db:5432/recruitpro
      - RECRUITPRO_REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  db:
    image: postgres:14
    environment:
      - POSTGRES_DB=recruitpro
      - POSTGRES_USER=recruitpro
      - POSTGRES_PASSWORD=changeme
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redisdata:/data

volumes:
  pgdata:
  redisdata:
```

---

## Security Architecture

### Defense in Depth

```
┌────────────────────────────────────────────────────────┐
│  Layer 1: Network Security                            │
│  - Firewall rules (only 80/443 open)                  │
│  - DDoS protection (CloudFlare)                       │
│  - IP whitelisting (admin endpoints)                  │
└────────────────────────────────────────────────────────┘
                        │
┌────────────────────────▼───────────────────────────────┐
│  Layer 2: Transport Security                          │
│  - TLS 1.2+ (HTTPS only in production)                │
│  - Certificate pinning (future)                       │
│  - HSTS headers                                       │
└────────────────────────────────────────────────────────┘
                        │
┌────────────────────────▼───────────────────────────────┐
│  Layer 3: Application Security                        │
│  - JWT authentication (stateless)                     │
│  - Role-based access control (RBAC)                   │
│  - Input validation (Pydantic)                        │
│  - SQL injection prevention (ORM)                     │
│  - XSS prevention (template escaping)                 │
│  - CSRF protection (SameSite cookies)                 │
│  - Rate limiting (SlowAPI)                            │
└────────────────────────────────────────────────────────┘
                        │
┌────────────────────────▼───────────────────────────────┐
│  Layer 4: Data Security                               │
│  - Password hashing (PBKDF2-SHA256)                   │
│  - Sensitive field encryption (AES-256-GCM)           │
│  - Audit logging (activity_feed)                      │
│  - Data retention policies                            │
└────────────────────────────────────────────────────────┘
                        │
┌────────────────────────▼───────────────────────────────┐
│  Layer 5: Infrastructure Security                     │
│  - OS hardening (CIS benchmarks)                      │
│  - Least privilege (separate users)                   │
│  - Automated patching                                 │
│  - Backup encryption                                  │
└────────────────────────────────────────────────────────┘
```

### Authentication Flow

```
1. User submits email + password
       │
       ▼
2. Server validates credentials
       ├─ Hash password
       ├─ Compare with database
       └─ Check account status
       │
       ▼
3. Generate JWT token
       ├─ Payload: {user_id, role, exp}
       ├─ Sign with secret key (HS256)
       └─ Set expiry (default 60 min)
       │
       ▼
4. Return token to client
       │
       ▼
5. Client stores token (localStorage)
       │
       ▼
6. Subsequent requests include:
   Authorization: Bearer <token>
       │
       ▼
7. Server validates token
       ├─ Verify signature
       ├─ Check expiry
       ├─ Load user from database
       └─ Inject into request context
       │
       ▼
8. Request processed with user context
```

### Authorization Model

**Role Hierarchy**:
```
super_admin
    │
    ├─ Full system access
    ├─ Can manage all users
    ├─ Can access all projects/candidates
    └─ Can configure integrations

admin
    │
    ├─ Workspace management
    ├─ User role assignment
    ├─ Integration configuration
    └─ View all activity

recruiter
    │
    ├─ Manage own projects
    ├─ Manage own candidates
    ├─ Use AI features
    └─ View own activity
```

**Permission Matrix**:

| Resource | recruiter | admin | super_admin |
|----------|-----------|-------|-------------|
| Own projects | CRUD | CRUD | CRUD |
| All projects | Read | CRUD | CRUD |
| Own candidates | CRUD | CRUD | CRUD |
| All candidates | Read | CRUD | CRUD |
| Users | - | Read, Update role | CRUD |
| Integrations | - | Configure | Configure |
| System settings | - | Read | CRUD |

---

## Technology Stack

### Backend Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Language** | Python | 3.11+ | Core programming language |
| **Web Framework** | FastAPI | 0.111.0+ | REST API framework |
| **ASGI Server** | Uvicorn | 0.30.0+ | Production server |
| **ORM** | SQLAlchemy | 2.0.30+ | Database abstraction |
| **Migration** | Alembic | 1.13.0+ | Schema versioning |
| **Validation** | Pydantic | 2.3.0+ | Data validation |
| **Authentication** | python-jose | 3.3.0+ | JWT handling |
| **Password Hashing** | passlib + bcrypt | 1.7.4+ | Secure password storage |
| **HTTP Client** | httpx | 0.27.0+ | Async HTTP requests |
| **Background Jobs** | Redis + RQ | 5.0.0+, 1.16.0+ | Async task processing |
| **Rate Limiting** | slowapi | 0.1.9+ | API throttling |
| **Monitoring** | Sentry SDK | 2.0.0+ | Error tracking |
| **Metrics** | Prometheus Client | 0.20.0+ | Observability |
| **Testing** | pytest | 8.2.1+ | Unit/integration tests |

### Frontend Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Templating** | Jinja2 | 3.1.3+ | Server-side rendering |
| **CSS Framework** | Tailwind CSS | 3.4.0+ | Utility-first styling |
| **CSS Processing** | PostCSS | 8.4.32+ | CSS compilation |
| **JavaScript** | ES6+ | - | Client-side logic |
| **Build Tool** | npm | 10.0.0+ | Package management |

### Database Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Production DB** | PostgreSQL | 14+ | Relational database |
| **Development DB** | SQLite | 3.x | Lightweight database |
| **Cache/Queue** | Redis | 5.0+ | In-memory data store |
| **File Storage** | S3-compatible | - | Object storage |

### Desktop Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Framework** | Electron | 29.1.0+ | Cross-platform desktop |
| **Build Tool** | electron-builder | 24.9.1+ | Installer creation |
| **Updater** | electron-updater | 6.1.8+ | Auto-updates |

### DevOps Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Container** | Docker | Containerization |
| **Orchestration** | Docker Compose | Multi-container apps |
| **Reverse Proxy** | Nginx | Load balancing, SSL |
| **Process Manager** | systemd | Service management |
| **CI/CD** | GitHub Actions | Automated testing/deployment |
| **Monitoring** | Sentry, Prometheus | Error tracking, metrics |

---

## Design Patterns

### 1. **Repository Pattern**

**Purpose**: Separate data access logic from business logic

**Implementation**:
```python
# app/models/candidate.py
class Candidate(Base):
    # Model definition

    @classmethod
    def get_by_id(cls, db: Session, candidate_id: str):
        return db.query(cls).filter(cls.candidate_id == candidate_id).first()

    @classmethod
    def list_by_project(cls, db: Session, project_id: str):
        return db.query(cls).filter(cls.project_id == project_id).all()
```

### 2. **Dependency Injection**

**Purpose**: Loose coupling, testability

**Implementation**:
```python
# app/deps.py
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    # Validate token, load user
    return user

# app/routers/candidates.py
@router.get("/")
def list_candidates(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # Use injected dependencies
    pass
```

### 3. **Service Layer Pattern**

**Purpose**: Encapsulate business logic

**Implementation**:
```python
# app/services/gemini.py
class GeminiService:
    def __init__(self, api_key: str):
        self.client = httpx.Client(base_url="...")

    def screen_cv(self, cv_text: str, requirements: dict) -> dict:
        # Business logic here
        pass
```

### 4. **Factory Pattern**

**Purpose**: Application initialization

**Implementation**:
```python
# app/main.py
def create_app() -> FastAPI:
    app = FastAPI(title="RecruitPro")

    # Register routers
    app.include_router(auth_router)
    app.include_router(projects_router)

    # Add middleware
    app.add_middleware(CORSMiddleware, ...)

    return app

app = create_app()
```

### 5. **Strategy Pattern** (Fallback Logic)

**Purpose**: Swap AI provider or fallback to heuristics

**Implementation**:
```python
# app/services/gemini.py
def screen_cv(self, cv_text: str, requirements: dict) -> dict:
    try:
        # Primary strategy: Gemini API
        return self._gemini_screen_cv(cv_text, requirements)
    except Exception as e:
        # Fallback strategy: Heuristic-based
        return self._fallback_screen_cv(cv_text, requirements)
```

### 6. **Observer Pattern** (Events)

**Purpose**: Decouple activity logging from business logic

**Implementation**:
```python
# app/services/events.py
def publish_sync(event_type: str, data: dict):
    # Log to activity_feed
    # Send SSE to connected clients
    pass

# Usage in routers
events.publish_sync("candidate_added", {"candidate_id": "123"})
```

---

## Scalability and Performance

### Horizontal Scaling Strategy

**Stateless Design**:
- No server-side sessions (JWT auth)
- Shared database (PostgreSQL)
- Shared file storage (S3)
- Shared queue (Redis)

**Load Balancing**:
```
Internet → Load Balancer → [App Server 1, App Server 2, App Server 3]
                              ↓            ↓            ↓
                           PostgreSQL (Master-Slave Replication)
                           Redis (Cluster Mode)
                           S3 (Object Storage)
```

### Performance Optimization

**Database**:
- Indexes on foreign keys, status fields, created_at
- Connection pooling (pool_size=20, max_overflow=30)
- Query optimization (select only needed columns)
- Pagination (limit API results)

**Caching**:
- Redis for session caching (future)
- API response caching (future)
- Salary benchmark caching (90 days)

**Background Jobs**:
- Async processing for AI operations
- Priority queues (high for user-initiated)
- Worker scaling (multiple RQ workers)

**File Uploads**:
- Chunked uploads for large files
- Direct S3 upload (pre-signed URLs, future)
- CDN for file delivery (CloudFront)

---

## Disaster Recovery

### Backup Strategy

**Database**:
- Daily full backups (automated)
- Point-in-time recovery (PostgreSQL WAL)
- Retention: 30 days
- Offsite storage (S3 Glacier)

**File Storage**:
- S3 versioning enabled
- Cross-region replication
- Retention: indefinite

**Recovery Objectives**:
- **RPO** (Recovery Point Objective): 24 hours
- **RTO** (Recovery Time Objective): 4 hours

### High Availability

**Database**:
- Master-slave replication (read replicas)
- Automatic failover (Patroni, PgBouncer)

**Application**:
- Multiple app server instances
- Health check endpoints (`/api/health`)
- Automatic restart (systemd, Docker)

**Monitoring**:
- Uptime monitoring (UptimeRobot, Pingdom)
- Error tracking (Sentry)
- Metrics (Prometheus + Grafana)
- Alerting (PagerDuty, email)

---

**Document Approval:**

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Chief Architect | [Name] | ___________ | ________ |
| Lead Developer | [Name] | ___________ | ________ |
| DevOps Lead | [Name] | ___________ | ________ |

---

**End of System Architecture Document**
