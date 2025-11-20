# RECRUITPRO - PROFESSIONAL DOCUMENTATION SUITE

## Document 1: Requirements Management Specification (RMS)

### 1.1 DOCUMENT CONTROL

| Attribute | Value |
|-----------|-------|
| Document ID | RMS-RECRUITPRO-001 |
| Version | 1.0 |
| Status | Draft |
| Classification | Internal |
| Owner | Requirements Manager |
| Approved By | [Pending] |
| Approval Date | [Pending] |
| Next Review | [90 days from approval] |

### 1.2 STAKEHOLDER REQUIREMENTS (SR)

#### SR-001: User Management
**Priority:** P0 (Critical)  
**Category:** Security & Access Control  
**Stakeholder:** All Users, System Administrators

**Description:**  
The system shall provide comprehensive user management capabilities including registration, authentication, authorization, and role-based access control.

**Acceptance Criteria:**
- AC-001-01: System shall support email-based user registration
- AC-001-02: System shall enforce password complexity (min 8 chars, 1 upper, 1 lower, 1 number)
- AC-001-03: System shall issue JWT tokens with 24-hour expiry
- AC-001-04: System shall support roles: super_admin, admin, recruiter, viewer
- AC-001-05: System shall log all authentication attempts (success/failure)

**Regulatory Requirements:** GDPR Art. 32 (Security of Processing)

**Dependencies:** None

**Verification Method:** Automated Testing + Manual Security Audit

---

#### SR-002: Project Management
**Priority:** P0 (Critical)  
**Category:** Core Business Logic  
**Stakeholder:** Recruitment Managers, Team Leads

**Description:**  
The system shall enable creation, management, and tracking of recruitment projects with full lifecycle support.

**Acceptance Criteria:**
- AC-002-01: User shall create project with mandatory fields: name, sector, location_region
- AC-002-02: System shall auto-generate unique project_id (format: proj_[12-char-hash])
- AC-002-03: Project status shall support: active, on_hold, completed, archived
- AC-002-04: System shall track target_hires vs actual hires_count
- AC-002-05: System shall support project tags (min 0, max 20 tags)
- AC-002-06: System shall enforce creator ownership (created_by field)
- AC-002-07: System shall cascade delete positions when project deleted

**Business Rules:**
- BR-002-01: Only project creator or admin can delete project
- BR-002-02: Archived projects are read-only
- BR-002-03: Projects with active positions cannot be archived

**Dependencies:** SR-001 (User Management)

**Verification Method:** Integration Testing + UAT

---

#### SR-003: Position Management
**Priority:** P0 (Critical)  
**Category:** Core Business Logic  
**Stakeholder:** Recruitment Managers, Recruiters

**Description:**  
The system shall manage job positions within projects, including creation, updates, and applicant tracking.

**Acceptance Criteria:**
- AC-003-01: Position shall be linked to parent project via project_id (FK)
- AC-003-02: System shall support position status: draft, open, closed
- AC-003-03: System shall track applicants count per position
- AC-003-04: System shall support multiple openings per position
- AC-003-05: Position shall store: title, department, experience_level, location, description

**Business Rules:**
- BR-003-01: Position cannot be created without valid project
- BR-003-02: Closed positions cannot accept new applicants
- BR-003-03: Experience levels: junior, mid, senior, lead, executive

**Dependencies:** SR-002 (Project Management)

**Verification Method:** Integration Testing

---

#### SR-004: Candidate Management
**Priority:** P0 (Critical)  
**Category:** Core Business Logic  
**Stakeholder:** Recruiters, Hiring Managers

**Description:**  
The system shall provide comprehensive candidate lifecycle management including sourcing, screening, interviewing, and hiring.

**Acceptance Criteria:**
- AC-004-01: System shall support candidate creation with: name, email, phone, current_title
- AC-004-02: System shall enforce email uniqueness per project
- AC-004-03: System shall track candidate status: new, screening, interview, offer, hired, rejected
- AC-004-04: System shall support candidate rating (1-5 scale)
- AC-004-05: System shall store resume file (PDF, DOCX, max 5MB)
- AC-004-06: System shall track candidate source (linkedin, referral, website, etc.)
- AC-004-07: System shall maintain status history with timestamps and user tracking

**Business Rules:**
- BR-004-01: Candidate email must be valid format
- BR-004-02: Resume file required before moving to screening
- BR-004-03: Only recruiters and admins can change candidate status
- BR-004-04: Status changes must be logged with reason

**Data Retention:** 
- Active candidates: Indefinite
- Rejected candidates: 12 months
- GDPR "Right to be Forgotten" applies

**Dependencies:** SR-002, SR-003

**Verification Method:** End-to-End Testing + GDPR Compliance Audit

---

#### SR-005: AI-Powered Resume Screening
**Priority:** P1 (High)  
**Category:** AI/ML Feature  
**Stakeholder:** Recruiters, Hiring Managers

**Description:**  
The system shall provide automated resume analysis using AI to score candidates against position requirements.

**Acceptance Criteria:**
- AC-005-01: System shall extract text from PDF/DOCX resumes
- AC-005-02: System shall generate scoring: skills_match, experience_match, education_match, cultural_fit
- AC-005-03: Overall score shall be weighted average (Skills 30%, Experience 30%, Education 20%, Culture 20%)
- AC-005-04: System shall provide: strengths list (min 3), concerns list (min 2), key highlights
- AC-005-05: System shall recommend: strong_yes, yes, maybe, no, strong_no
- AC-005-06: Screening shall complete within 30 seconds
- AC-005-07: System shall log all AI screening jobs with input/output for audit

**Performance Requirements:**
- PR-005-01: Screening accuracy: >85% correlation with human recruiters
- PR-005-02: Maximum processing time: 30 seconds per resume
- PR-005-03: System shall queue requests if AI service unavailable

**Regulatory Requirements:** 
- EU AI Act (High-Risk AI System)
- GDPR Art. 22 (Automated Decision Making)

**Dependencies:** SR-004, SR-003

**Verification Method:** AI Model Validation + Bias Testing + UAT

---

#### SR-006: Document Processing
**Priority:** P1 (High)  
**Category:** AI/ML Feature  
**Stakeholder:** Project Managers, Recruiters

**Description:**  
The system shall automatically analyze project briefs and extract position requirements.

**Acceptance Criteria:**
- AC-006-01: System shall accept PDF, DOCX, TXT files (max 10MB)
- AC-006-02: System shall extract: project name, sector, positions, requirements, locations
- AC-006-03: System shall auto-create positions from extracted data
- AC-006-04: System shall provide confidence score for each extraction
- AC-006-05: User shall review and approve before position creation

**Business Rules:**
- BR-006-01: Extracted data is suggestion only, requires human approval
- BR-006-02: Failed extraction shall not block manual position creation

**Dependencies:** SR-002, SR-003

**Verification Method:** Integration Testing + UAT

---

#### SR-007: Salary Benchmarking
**Priority:** P2 (Medium)  
**Category:** Market Intelligence  
**Stakeholder:** Recruiters, Hiring Managers, Clients

**Description:**  
The system shall provide salary benchmarking data based on role, region, sector, and seniority.

**Acceptance Criteria:**
- AC-007-01: System shall return: annual_min, annual_mid, annual_max for given parameters
- AC-007-02: System shall support multiple currencies
- AC-007-03: System shall provide rationale and sources for benchmark
- AC-007-04: Benchmarks shall be stored and reusable
- AC-007-05: Benchmarks older than 6 months shall be flagged as stale

**Data Sources:**
- Glassdoor API (if available)
- Indeed Salary Data
- LinkedIn Salary Insights
- Internal historical data

**Dependencies:** None

**Verification Method:** Data Accuracy Validation + UAT

---

#### SR-008: Activity Logging & Audit Trail
**Priority:** P1 (High)  
**Category:** Security & Compliance  
**Stakeholder:** System Administrators, Compliance Officers

**Description:**  
The system shall maintain comprehensive audit trail of all user actions and system events.

**Acceptance Criteria:**
- AC-008-01: System shall log: event_type, user_id, resource_id, timestamp, details
- AC-008-02: Logs shall be immutable (append-only)
- AC-008-03: Logs shall be retained for minimum 7 years
- AC-008-04: System shall support log filtering by: user, date range, event type, resource
- AC-008-05: Critical events shall trigger real-time alerts

**Event Types:**
- Authentication (login, logout, failed_login)
- Data modification (create, update, delete)
- Status changes (candidate, project, position)
- AI operations (screening, document_analysis, sourcing)
- Admin operations (user_creation, permission_change, config_update)

**Regulatory Requirements:** 
- GDPR Art. 30 (Records of Processing Activities)
- SOC 2 Type II (Audit Logging)

**Dependencies:** All SRs

**Verification Method:** Security Audit + Compliance Review

---

#### SR-009: Interview Management
**Priority:** P2 (Medium)  
**Category:** Recruitment Process  
**Stakeholder:** Recruiters, Hiring Managers

**Description:**  
The system shall manage interview scheduling, feedback collection, and evaluation.

**Acceptance Criteria:**
- AC-009-01: System shall support interview types: phone, video, in_person, technical
- AC-009-02: System shall track: interviewer, datetime, duration, stage
- AC-009-03: System shall collect structured feedback with ratings
- AC-009-04: System shall support multiple interview rounds per candidate

**Business Rules:**
- BR-009-01: Candidate must be in "interview" status to schedule
- BR-009-02: Interview feedback required before progressing candidate

**Dependencies:** SR-004

**Verification Method:** Integration Testing

---

#### SR-010: Communication Templates
**Priority:** P2 (Medium)  
**Category:** Automation  
**Stakeholder:** Recruiters

**Description:**  
The system shall provide templated communication for candidate outreach and follow-ups.

**Acceptance Criteria:**
- AC-010-01: System shall support template types: initial_outreach, follow_up, interview_invite, offer, rejection
- AC-010-02: Templates shall support variables: {candidate_name}, {position_title}, {company_name}
- AC-010-03: AI shall personalize templates based on candidate profile
- AC-010-04: Users shall create custom templates

**Dependencies:** SR-004, SR-005

**Verification Method:** UAT

---

### 1.3 FUNCTIONAL REQUIREMENTS (FR)

#### FR-AUTH: Authentication & Authorization

**FR-AUTH-001: User Registration**
- Input: email (valid format), name (2-100 chars), password (8-64 chars)
- Process: Validate inputs → Hash password (bcrypt) → Generate user_id → Insert DB → Return success
- Output: user_id, email, name, role
- Error Cases: Duplicate email, Invalid email format, Weak password

**FR-AUTH-002: User Login**
- Input: email, password
- Process: Lookup user → Verify password hash → Generate JWT token (24h expiry) → Log activity
- Output: access_token, token_type, user_id, role
- Error Cases: Invalid credentials, Account disabled

**FR-AUTH-003: Token Validation**
- Input: JWT token (Authorization header)
- Process: Decode JWT → Validate signature → Check expiry → Extract user_id → Fetch user from DB
- Output: User object
- Error Cases: Invalid token, Expired token, User not found

**FR-AUTH-004: Role-Based Access Control**
- Roles: super_admin (all permissions), admin (project management, user view), recruiter (candidate management), viewer (read-only)
- Process: Extract role from authenticated user → Check permission for requested resource → Allow/Deny
- Error Cases: Insufficient permissions

---

#### FR-PROJ: Project Management

**FR-PROJ-001: Create Project**
- Input: name, sector, location_region, summary, client, priority, target_hires
- Process: Validate inputs → Generate project_id → Set created_by → Insert DB → Log activity
- Output: Project object
- Validation: name (required, 2-200 chars), sector (optional), priority (low|medium|high)

**FR-PROJ-002: List Projects**
- Input: filters (status, sector, priority), pagination (page, limit)
- Process: Build query → Apply filters → Sort by created_at DESC → Return paginated results
- Output: Array of projects, total_count, page, limit
- Performance: Max 50 projects per request

**FR-PROJ-003: Update Project**
- Input: project_id, updated fields
- Process: Fetch project → Check ownership → Validate inputs → Update DB → Log activity
- Output: Updated project object
- Business Rules: Only creator or admin can update

**FR-PROJ-004: Delete Project**
- Input: project_id
- Process: Fetch project → Check ownership → Cascade delete positions → Delete project → Log activity
- Output: Success message
- Side Effects: All associated positions, candidates, documents deleted

---

#### FR-POS: Position Management

**FR-POS-001: Create Position**
- Input: project_id, title, department, experience_level, location, description, openings
- Process: Validate project exists → Generate position_id → Insert DB → Log activity
- Output: Position object
- Validation: title (required), openings (min 1, max 100)

**FR-POS-002: List Positions**
- Input: project_id (optional), filters (status, department)
- Process: Build query → Apply filters → Return results
- Output: Array of positions

**FR-POS-003: Update Position Status**
- Input: position_id, status (draft|open|closed)
- Process: Fetch position → Validate status transition → Update DB → Log activity
- Output: Updated position
- Business Rules: draft → open → closed (unidirectional)

---

#### FR-CAND: Candidate Management

**FR-CAND-001: Create Candidate**
- Input: project_id, position_id, name, email, phone, resume_file
- Process: Validate email format → Upload resume → Generate candidate_id → Insert DB → Log activity
- Output: Candidate object
- Validation: email (unique per project), resume (PDF/DOCX, max 5MB)

**FR-CAND-002: Update Candidate Status**
- Input: candidate_id, new_status, reason
- Process: Fetch candidate → Validate status transition → Insert status_history → Update DB → Log activity
- Output: Updated candidate
- Status Flow: new → screening → interview → offer → hired (or rejected at any stage)

**FR-CAND-003: Rate Candidate**
- Input: candidate_id, rating (1-5)
- Process: Fetch candidate → Update rating → Log activity
- Output: Updated candidate

**FR-CAND-004: Bulk Status Update**
- Input: candidate_ids[], new_status, reason
- Process: For each candidate → Validate → Update status → Insert history → Log
- Output: Success count, failure count
- Performance: Max 100 candidates per request

---

#### FR-AI-SCREEN: AI Resume Screening

**FR-AI-SCREEN-001: Screen Candidate**
- Input: candidate_id, position_id
- Process: 
  1. Fetch candidate resume and position requirements
  2. Extract resume text
  3. Build AI prompt with scoring criteria
  4. Call Gemini API
  5. Parse JSON response
  6. Store screening results
  7. Update candidate with scores
  8. Log AI job
- Output: Screening object (scores, strengths, concerns, recommendation)
- Performance: Max 30 seconds
- Error Handling: Queue retry on API failure (max 3 attempts)

**FR-AI-SCREEN-002: Batch Screen**
- Input: position_id (screen all new candidates)
- Process: Fetch all candidates with status=new → Queue individual screening jobs → Execute async
- Output: Job IDs array
- Performance: Max 10 concurrent screenings

---

#### FR-AI-DOC: Document Processing

**FR-AI-DOC-001: Analyze Project Brief**
- Input: document_id
- Process:
  1. Fetch document from storage
  2. Extract text (PDF/DOCX parser)
  3. Build AI prompt for position extraction
  4. Call Gemini API
  5. Parse extracted positions
  6. Return suggestions (not auto-create)
- Output: Array of suggested positions with confidence scores
- Error Handling: Return empty array on failure, log error

---

### 1.4 NON-FUNCTIONAL REQUIREMENTS (NFR)

#### NFR-PERF: Performance

**NFR-PERF-001: API Response Time**
- Requirement: 95th percentile < 500ms for GET requests, < 1s for POST/PUT
- Measurement: APM monitoring
- Target: Sustained under 100 concurrent users

**NFR-PERF-002: Database Query Performance**
- Requirement: All queries < 100ms
- Indexes: user(email), project(created_by), candidate(email, project_id), position(project_id)

**NFR-PERF-003: AI Processing**
- Resume screening: < 30s
- Document analysis: < 60s
- Timeout: 120s (then queue retry)

---

#### NFR-SEC: Security

**NFR-SEC-001: Authentication**
- JWT tokens with HMAC-SHA256 signing
- Token expiry: 24 hours
- Refresh token: Not implemented (requires re-login)

**NFR-SEC-002: Password Security**
- Hashing: bcrypt (cost factor 12)
- Minimum complexity: 8 chars, 1 upper, 1 lower, 1 number
- No password history (recommended: implement 5 previous passwords)

**NFR-SEC-003: Data Encryption**
- At Rest: SQLite encryption (SQLCipher recommended)
- In Transit: HTTPS only (TLS 1.2+)
- Sensitive Fields: Integration credentials encrypted with AES-256

**NFR-SEC-004: SQL Injection Prevention**
- ORM parameterized queries (SQLAlchemy)
- Input validation (Pydantic schemas)

**NFR-SEC-005: XSS Prevention**
- Output encoding (Jinja2 auto-escape)
- Content Security Policy headers

---

#### NFR-SCALE: Scalability

**NFR-SCALE-001: Horizontal Scaling**
- Stateless API design
- Session data in JWT (no server-side sessions)
- File storage: External (S3-compatible)

**NFR-SCALE-002: Database Connection Pooling**
- Pool size: 20 connections
- Overflow: 10 connections
- Timeout: 30s

---

#### NFR-USABILITY

**NFR-USABILITY-001: Response Times**
- Page load: < 2s
- Search results: < 1s
- Form submission feedback: < 500ms

**NFR-USABILITY-002: Accessibility**
- WCAG 2.1 Level AA compliance
- Keyboard navigation support
- Screen reader compatible

---

#### NFR-AVAIL: Availability

**NFR-AVAIL-001: Uptime**
- Target: 99.5% uptime (3.65 hours downtime/month)
- Monitoring: Health check endpoint (/api/health)

**NFR-AVAIL-002: Backup**
- Database backup: Daily (retained 30 days)
- File backup: Daily incremental, weekly full

---

### 1.5 REQUIREMENT DEPENDENCIES MATRIX

| Requirement | Depends On | Dependency Type |
|-------------|------------|-----------------|
| SR-002 (Project) | SR-001 (User) | Mandatory |
| SR-003 (Position) | SR-002 (Project) | Mandatory |
| SR-004 (Candidate) | SR-002, SR-003 | Mandatory |
| SR-005 (AI Screening) | SR-004 (Candidate) | Mandatory |
| SR-006 (Doc Processing) | SR-002 (Project) | Optional |
| SR-007 (Salary) | None | Optional |
| SR-008 (Logging) | All | Cross-cutting |
| SR-009 (Interview) | SR-004 (Candidate) | Optional |
| SR-010 (Templates) | SR-004 (Candidate) | Optional |

---

### 1.6 REQUIREMENT CHANGE MANAGEMENT

**Change Request Process:**
1. Stakeholder submits CR form with justification
2. Requirements Manager reviews impact analysis
3. Architecture review for technical feasibility
4. Prioritization by Product Owner
5. Approval by Change Control Board
6. Update traceability matrix
7. Notify affected teams

**Change Classification:**
- **Critical:** Security, data loss, regulatory compliance (24h response)
- **High:** Core functionality, performance degradation (72h response)
- **Medium:** Feature enhancement, usability (1 week response)
- **Low:** Nice-to-have, cosmetic (2 weeks response)

---

## Document 2: Traceability Matrix (RTM)

### 2.1 REQUIREMENTS TO DESIGN TRACEABILITY

| Req ID | Requirement Name | Design Component | Verification Method | Status |
|--------|------------------|------------------|---------------------|--------|
| SR-001 | User Management | User model, AuthRouter, JWT middleware | Unit tests, Security audit | Implemented |
| SR-002 | Project Management | Project model, ProjectsRouter | Integration tests | Implemented |
| SR-003 | Position Management | Position model, PositionsRouter | Integration tests | Implemented |
| SR-004 | Candidate Management | Candidate model, CandidatesRouter | E2E tests | Implemented |
| SR-005 | AI Screening | GeminiService.screen_candidate() | AI validation, UAT | Implemented |
| SR-006 | Doc Processing | GeminiService.analyze_document() | Integration tests | Implemented |
| SR-007 | Salary Benchmarking | GeminiService.benchmark_salary() | Data accuracy validation | Implemented |
| SR-008 | Activity Logging | ActivityLog model, ActivityRouter | Audit review | Implemented |
| SR-009 | Interview Management | Interview model, InterviewRouter | Integration tests | Implemented |
| SR-010 | Communication Templates | CommunicationTemplate model | UAT | Implemented |

### 2.2 DESIGN TO CODE TRACEABILITY

| Design Component | Source File | Key Functions/Classes | LOC | Test Coverage |
|------------------|-------------|------------------------|-----|---------------|
| User model | app/models/__init__.py | User class | 15 | 85% |
| AuthRouter | app/routers/auth.py | register(), login() | 120 | 90% |
| Project model | app/models/__init__.py | Project class | 30 | 80% |
| ProjectsRouter | app/routers/projects.py | create_project(), list_projects() | 200 | 75% |
| Position model | app/models/__init__.py | Position class | 25 | 80% |
| Candidate model | app/models/__init__.py | Candidate class | 35 | 70% |
| GeminiService | app/services/gemini.py | screen_candidate(), analyze_document() | 500 | 60% |
| ActivityLog model | app/models/__init__.py | ActivityLog class | 20 | 85% |

### 2.3 CODE TO TEST TRACEABILITY

| Test Case ID | Test Name | Requirement Covered | Test Type | Automated | Pass/Fail |
|--------------|-----------|---------------------|-----------|-----------|-----------|
| TC-AUTH-001 | Test user registration | SR-001, FR-AUTH-001 | Unit | Yes | Pass |
| TC-AUTH-002 | Test user login | SR-001, FR-AUTH-002 | Unit | Yes | Pass |
| TC-AUTH-003 | Test invalid credentials | SR-001, FR-AUTH-002 | Unit | Yes | Pass |
| TC-AUTH-004 | Test token expiry | SR-001, FR-AUTH-003 | Unit | Yes | Pass |
| TC-PROJ-001 | Test create project | SR-002, FR-PROJ-001 | Integration | Yes | Pass |
| TC-PROJ-002 | Test list projects | SR-002, FR-PROJ-002 | Integration | Yes | Pass |
| TC-PROJ-003 | Test unauthorized delete | SR-002, FR-PROJ-004 | Integration | Yes | Pass |
| TC-POS-001 | Test create position | SR-003, FR-POS-001 | Integration | Yes | Pass |
| TC-CAND-001 | Test create candidate | SR-004, FR-CAND-001 | Integration | Yes | Pass |
| TC-CAND-002 | Test status update | SR-004, FR-CAND-002 | Integration | Yes | Pass |
| TC-AI-001 | Test resume screening | SR-005, FR-AI-SCREEN-001 | Integration | Yes | Pass |
| TC-AI-002 | Test document analysis | SR-006, FR-AI-DOC-001 | Integration | Yes | Pass |
| TC-SEC-001 | Test SQL injection prevention | NFR-SEC-004 | Security | Yes | Pass |
| TC-PERF-001 | Test API response time | NFR-PERF-001 | Performance | Yes | Pass |

### 2.4 TEST TO DEFECT TRACEABILITY

| Defect ID | Description | Related Test | Requirement | Severity | Status |
|-----------|-------------|--------------|-------------|----------|--------|
| BUG-001 | Nullable foreign key allows orphaned records | TC-PROJ-003 | SR-002 | High | Open |
| BUG-002 | No password complexity validation | TC-AUTH-001 | NFR-SEC-002 | Critical | Open |
| BUG-003 | Resume file size not validated | TC-CAND-001 | SR-004 | Medium | Open |
| BUG-004 | AI screening timeout not handled | TC-AI-001 | NFR-PERF-003 | High | Open |
| BUG-005 | No soft delete for candidates (GDPR violation) | TC-CAND-002 | SR-004 | Critical | Open |

---

## Document 3: Development Standards & Guidelines

### 3.1 DATABASE DESIGN STANDARDS

#### STANDARD-DB-001: Table Naming
- **Rule:** Use plural nouns (users, projects, candidates)
- **Rationale:** Clarity that table contains multiple records
- **Example:** `users` not `user`, `projects` not `project`
- **Enforcement:** Code review checklist

#### STANDARD-DB-002: Primary Keys
- **Rule:** Use semantic string IDs with prefix (e.g., usr_abc123, proj_xyz789)
- **Format:** `{3-letter-prefix}_{12-char-alphanumeric}`
- **Rationale:** Human-readable, avoids sequence leakage, supports distributed systems
- **Implementation:**
```python
import secrets
import string

def generate_id(prefix: str) -> str:
    chars = string.ascii_lowercase + string.digits
    random_part = ''.join(secrets.choice(chars) for _ in range(12))
    return f"{prefix}_{random_part}"
```
- **Enforcement:** Database factory functions

#### STANDARD-DB-003: Foreign Keys
- **Rule:** NEVER allow NULL foreign keys unless explicitly required for soft relationships
- **Rationale:** Data integrity, prevents orphaned records
- **Implementation:** `nullable=False` in SQLAlchemy Column definition
- **Exception Process:** Requires architecture review approval
- **Current Violations:** 
  - projects.created_by (nullable=True) ❌
  - candidates.created_by (nullable=True) ❌
  - **FIX REQUIRED**

#### STANDARD-DB-004: Cascade Behavior
- **Rule:** Define explicit cascade for all relationships
  - Parent-child ownership: `CASCADE DELETE`
  - Reference relationships: `SET NULL` or `RESTRICT`
- **Example:**
```python
# Parent-child (project owns positions)
positions = relationship("Position", back_populates="project", 
                        cascade="all, delete")

# Reference (user created project, but user can be deleted)
created_by = Column(String, ForeignKey("users.user_id", ondelete="SET NULL"))
```

#### STANDARD-DB-005: Soft Delete
- **Rule:** All entities with PII or compliance data MUST support soft delete
- **Implementation:** Add `deleted_at` (DateTime, nullable=True), `deleted_by` (String, FK to users)
- **Query Modification:** Default filter `WHERE deleted_at IS NULL`
- **Rationale:** GDPR compliance, audit trail, data recovery
- **Applies To:** Users, Candidates, Projects
- **Current Status:** ❌ NOT IMPLEMENTED - CRITICAL GAP

#### STANDARD-DB-006: Timestamps
- **Rule:** All tables MUST have `created_at` and `updated_at`
- **Implementation:**
```python
created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
updated_at = Column(DateTime, default=datetime.utcnow, 
                   onupdate=datetime.utcnow, nullable=False)
```
- **Enforcement:** Automated schema validation

#### STANDARD-DB-007: JSON Columns
- **Rule:** Use JSON columns for:
  - Arrays of simple values (tags, team_members)
  - Flexible metadata
  - API responses that don't need querying
- **Anti-Pattern:** Storing relational data in JSON (e.g., candidate interviews)
- **Validation:** Pydantic schemas for JSON structure

#### STANDARD-DB-008: Indexes
- **Rule:** Index ALL foreign keys and frequently queried fields
- **Required Indexes:**
  - All FK columns
  - Unique constraints (email, etc.)
  - Status fields (status, priority)
  - Date fields used in range queries (created_at)
- **Enforcement:** Database migration review

#### STANDARD-DB-009: Enum Fields
- **Rule:** Use String columns with Pydantic enum validation (not native DB enums)
- **Rationale:** Easier migrations, better portability
- **Example:**
```python
from enum import Enum
from pydantic import BaseModel

class ProjectStatus(str, Enum):
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    ARCHIVED = "archived"

# In model
status = Column(String, nullable=False, default="active")

# In schema
class ProjectCreate(BaseModel):
    status: ProjectStatus = ProjectStatus.ACTIVE
```

---

### 3.2 API DESIGN STANDARDS

#### STANDARD-API-001: RESTful URL Structure
- **Rule:** Follow REST conventions strictly
- **Format:**
  - Collection: `GET /api/{resource}` (list)
  - Item: `GET /api/{resource}/{id}` (get by ID)
  - Create: `POST /api/{resource}` (create new)
  - Update: `PUT /api/{resource}/{id}` (full update)
  - Partial: `PATCH /api/{resource}/{id}` (partial update)
  - Delete: `DELETE /api/{resource}/{id}` (delete)
  - Actions: `POST /api/{resource}/{id}/{action}` (e.g., /api/candidates/{id}/screen)

#### STANDARD-API-002: Response Format
- **Rule:** Consistent JSON structure
- **Success Response:**
```json
{
  "success": true,
  "data": { /* resource or array */ },
  "meta": {
    "timestamp": "2025-01-15T10:30:00Z",
    "request_id": "req_abc123"
  }
}
```
- **Error Response:**
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid email format",
    "details": {
      "field": "email",
      "value": "not-an-email"
    }
  },
  "meta": {
    "timestamp": "2025-01-15T10:30:00Z",
    "request_id": "req_abc123"
  }
}
```

#### STANDARD-API-003: HTTP Status Codes
- **Rule:** Use semantically correct status codes
- **Mapping:**
  - 200 OK: Successful GET, PUT, PATCH
  - 201 Created: Successful POST with resource creation
  - 204 No Content: Successful DELETE
  - 400 Bad Request: Client error (validation failure)
  - 401 Unauthorized: Missing or invalid authentication
  - 403 Forbidden: Authenticated but insufficient permissions
  - 404 Not Found: Resource doesn't exist
  - 409 Conflict: Duplicate resource (email already exists)
  - 422 Unprocessable Entity: Semantic validation error
  - 429 Too Many Requests: Rate limit exceeded
  - 500 Internal Server Error: Unexpected server error
  - 503 Service Unavailable: Temporary outage (AI service down)

#### STANDARD-API-004: Pagination
- **Rule:** All list endpoints MUST support pagination
- **Query Parameters:**
  - `page` (default: 1, min: 1)
  - `limit` (default: 20, min: 1, max: 100)
  - `sort_by` (field name)
  - `order` (asc|desc, default: desc)
- **Response:**
```json
{
  "data": [ /* items */ ],
  "meta": {
    "page": 1,
    "limit": 20,
    "total_items": 150,
    "total_pages": 8
  }
}
```

#### STANDARD-API-005: Filtering
- **Rule:** Support query parameter filters
- **Format:** `/api/candidates?status=screening&rating>=4&project_id=proj_123`
- **Operators:** `=`, `!=`, `>`, `>=`, `<`, `<=`, `~` (contains)

#### STANDARD-API-006: Rate Limiting
- **Rule:** Implement rate limiting per user/IP
- **Limits:**
  - Authenticated: 1000 req/hour
  - Unauthenticated: 100 req/hour
  - AI endpoints: 50 req/hour
- **Response:** HTTP 429 with `Retry-After` header

#### STANDARD-API-007: Versioning
- **Rule:** API version in URL path
- **Format:** `/api/v1/{resource}`
- **Rationale:** Explicit, backward compatibility
- **Current State:** No versioning ❌ - IMPLEMENT BEFORE v1.0

#### STANDARD-API-008: Request ID
- **Rule:** Generate unique request_id for every request
- **Implementation:** Middleware adds `X-Request-ID` header
- **Usage:** Logging, debugging, support tickets
- **Format:** `req_{16-char-hash}`

---

### 3.3 AUTHENTICATION & AUTHORIZATION STANDARDS

#### STANDARD-AUTH-001: JWT Token Structure
- **Rule:** Use standardized JWT claims
- **Payload:**
```json
{
  "sub": "usr_abc123",  // Subject (user ID)
  "email": "user@example.com",
  "role": "recruiter",
  "exp": 1736939400,  // Expiration (Unix timestamp)
  "iat": 1736853000,  // Issued at
  "jti": "jwt_xyz789"  // JWT ID (for revocation)
}
```
- **Signing:** HMAC-SHA256 with secret from environment variable
- **Expiry:** 24 hours (configurable via `JWT_EXPIRY_HOURS`)

#### STANDARD-AUTH-002: Password Policy
- **Rule:** Enforce strong passwords
- **Requirements:**
  - Minimum 8 characters
  - Maximum 64 characters
  - At least 1 uppercase letter
  - At least 1 lowercase letter
  - At least 1 number
  - At least 1 special character (optional but recommended)
- **Implementation:** Pydantic validator
```python
from pydantic import validator
import re

@validator('password')
def validate_password(cls, v):
    if len(v) < 8:
        raise ValueError('Password must be at least 8 characters')
    if not re.search(r'[A-Z]', v):
        raise ValueError('Password must contain uppercase letter')
    if not re.search(r'[a-z]', v):
        raise ValueError('Password must contain lowercase letter')
    if not re.search(r'\d', v):
        raise ValueError('Password must contain number')
    return v
```
- **Current Status:** ❌ NOT IMPLEMENTED

#### STANDARD-AUTH-003: Role-Based Access Control (RBAC)
- **Rule:** Define permissions per role explicitly
- **Roles:**

| Role | Permissions |
|------|-------------|
| super_admin | All operations, system configuration, user management |
| admin | Create/update/delete projects, positions, candidates; view analytics |
| recruiter | Create/update candidates, update statuses, view own projects |
| viewer | Read-only access to assigned projects |

- **Implementation:** FastAPI dependency injection
```python
from fastapi import Depends, HTTPException

def require_role(allowed_roles: list[str]):
    async def check_role(user: User = Depends(get_current_user)):
        if user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return check_role

# Usage
@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    user: User = Depends(require_role(["super_admin", "admin"]))
):
    ...
```

#### STANDARD-AUTH-004: Sensitive Endpoint Protection
- **Rule:** All state-changing endpoints require authentication
- **Public Endpoints (whitelist):**
  - `POST /api/auth/register`
  - `POST /api/auth/login`
  - `GET /api/health`
  - `GET /api/version`
- **All others:** MUST use `Depends(get_current_user)`

---

### 3.4 AI INTEGRATION STANDARDS

#### STANDARD-AI-001: Prompt Engineering
- **Rule:** Version control all prompts in dedicated directory
- **Structure:**
```
app/prompts/
  ├── screening/
  │   ├── v1_basic.txt
  │   └── v2_detailed.txt
  ├── document_analysis/
  │   └── v1_extraction.txt
  ├── outreach/
  │   └── v1_email.txt
  └── __init__.py  # Prompt loader
```
- **Versioning:** Semantic versioning (v1, v2, v3...)
- **A/B Testing:** Support multiple prompt versions with performance tracking

#### STANDARD-AI-002: Response Validation
- **Rule:** ALWAYS validate AI responses with Pydantic schemas
- **Example:**
```python
from pydantic import BaseModel, Field

class ScreeningResult(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    skills_match: int = Field(ge=0, le=100)
    experience_match: int = Field(ge=0, le=100)
    education_match: int = Field(ge=0, le=100)
    cultural_fit: int = Field(ge=0, le=100)
    strengths: list[str] = Field(min_items=3)
    concerns: list[str] = Field(min_items=2)
    recommendation: str = Field(pattern='^(strong_yes|yes|maybe|no|strong_no)$')
    reasoning: str

# In service
response_data = await gemini_api.call(prompt)
try:
    result = ScreeningResult.model_validate(response_data)
except ValidationError as e:
    logger.error(f"AI response validation failed: {e}")
    raise AIServiceError("Invalid AI response format")
```

#### STANDARD-AI-003: Error Handling
- **Rule:** Implement retry logic with exponential backoff
- **Implementation:**
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def call_ai_service(prompt: str):
    try:
        response = await gemini.generate(prompt)
        return response
    except APIError as e:
        logger.warning(f"AI API error: {e}, retrying...")
        raise
```

#### STANDARD-AI-004: Logging & Audit
- **Rule:** Log ALL AI interactions for audit trail
- **Required Fields:**
  - job_id (unique identifier)
  - user_id (who triggered)
  - operation_type (screening, document_analysis, etc.)
  - input_summary (first 200 chars)
  - output_summary (first 200 chars)
  - tokens_used
  - duration_ms
  - status (success|failure)
  - error_message (if failed)
- **Retention:** Minimum 2 years (regulatory compliance)

#### STANDARD-AI-005: Bias Monitoring
- **Rule:** Track AI decision outcomes by demographic groups
- **Metrics:**
  - Screening pass rate by experience level
  - Recommendation distribution by source
  - False positive/negative rates
- **Review Frequency:** Quarterly
- **Threshold:** >10% disparity triggers investigation

#### STANDARD-AI-006: Human-in-the-Loop
- **Rule:** AI recommendations are SUGGESTIONS, not decisions
- **Implementation:**
  - All AI outputs labeled as "AI-Generated"
  - User must explicitly approve before taking action
  - Provide override mechanism
- **Example:** AI recommends "strong_no" → Recruiter can still progress candidate with justification

---

### 3.5 SECURITY STANDARDS

#### STANDARD-SEC-001: Input Validation
- **Rule:** Validate ALL user inputs with Pydantic schemas
- **Never Trust:**
  - URL parameters
  - Query strings
  - Request bodies
  - Headers (except standard HTTP headers)
- **Sanitization:** Strip HTML tags, escape SQL-unsafe characters

#### STANDARD-SEC-002: SQL Injection Prevention
- **Rule:** ONLY use ORM (SQLAlchemy) for database queries
- **Forbidden:** Raw SQL via `engine.execute()`
- **Exception Process:** Security team review required
- **Current Compliance:** ✅ Compliant

#### STANDARD-SEC-003: File Upload Security
- **Rule:** Validate file type, size, and content
- **Allowed Types:** PDF, DOCX (MIME type validation)
- **Max Size:** 5MB
- **Virus Scan:** Integrate ClamAV or VirusTotal API
- **Storage:** Isolated storage with no execution permissions
- **Naming:** Generate random filename (prevent directory traversal)
```python
import secrets

def secure_filename(original_name: str) -> str:
    ext = original_name.split('.')[-1]
    random_name = secrets.token_hex(16)
    return f"{random_name}.{ext}"
```

#### STANDARD-SEC-004: HTTPS Enforcement
- **Rule:** Production MUST use HTTPS
- **Implementation:** 
  - Redirect HTTP → HTTPS (301)
  - HSTS header (max-age=31536000)
  - Secure cookie flag

#### STANDARD-SEC-005: Secrets Management
- **Rule:** NEVER commit secrets to Git
- **Implementation:**
  - Environment variables (.env file, gitignored)
  - AWS Secrets Manager / Azure Key Vault for production
  - Rotate secrets quarterly
- **Current Violations:** Check .env.example exists and is documented

---

### 3.6 CODE QUALITY STANDARDS

#### STANDARD-CODE-001: Type Hints
- **Rule:** All functions MUST have type hints
- **Example:**
```python
def create_project(
    db: Session,
    name: str,
    user_id: str
) -> Project:
    ...
```
- **Enforcement:** MyPy linting in CI/CD

#### STANDARD-CODE-002: Docstrings
- **Rule:** All public functions have docstrings (Google style)
- **Example:**
```python
def screen_candidate(candidate_id: str, position_id: str) -> ScreeningResult:
    """Screen a candidate's resume against position requirements.
    
    Args:
        candidate_id: Unique identifier for the candidate
        position_id: Unique identifier for the position
        
    Returns:
        ScreeningResult object with scores and recommendations
        
    Raises:
        CandidateNotFoundError: If candidate doesn't exist
        AIServiceError: If AI service fails after retries
    """
    ...
```

#### STANDARD-CODE-003: Error Handling
- **Rule:** Use specific exception classes, never bare `except:`
- **Exception Hierarchy:**
```python
class RecruitProError(Exception):
    """Base exception for RecruitPro"""
    pass

class ResourceNotFoundError(RecruitProError):
    """Resource doesn't exist"""
    pass

class ValidationError(RecruitProError):
    """Input validation failed"""
    pass

class AuthenticationError(RecruitProError):
    """Authentication failed"""
    pass

class AIServiceError(RecruitProError):
    """AI service interaction failed"""
    pass
```

#### STANDARD-CODE-004: Logging
- **Rule:** Use structured logging with consistent format
- **Levels:**
  - DEBUG: Detailed flow, variable values
  - INFO: Major events (user login, project created)
  - WARNING: Recoverable errors (AI retry, validation failure)
  - ERROR: Unrecoverable errors (DB connection lost)
  - CRITICAL: System failure (data corruption)
- **Format:**
```python
import structlog

logger = structlog.get_logger()

logger.info(
    "candidate_created",
    candidate_id=candidate.candidate_id,
    project_id=candidate.project_id,
    user_id=user.user_id,
    duration_ms=duration
)
```

#### STANDARD-CODE-005: Testing
- **Rule:** Minimum 80% code coverage
- **Test Types:**
  - Unit: Test individual functions (fast, isolated)
  - Integration: Test API endpoints (database transactions)
  - E2E: Test full user flows (slow, comprehensive)
- **Naming Convention:** `test_{function_name}_{scenario}_{expected_result}`
- **Example:**
```python
def test_create_candidate_valid_data_returns_201():
    ...

def test_create_candidate_duplicate_email_returns_409():
    ...
```

---

### 3.7 DEPLOYMENT STANDARDS

#### STANDARD-DEPLOY-001: Environment Configuration
- **Rule:** Use environment-specific configs
- **Environments:**
  - **Development:** Local SQLite, debug mode, relaxed CORS
  - **Staging:** Postgres, production-like data, integration testing
  - **Production:** Postgres, strict security, monitoring enabled
- **Config Files:**
```
config/
  ├── development.env
  ├── staging.env
  └── production.env
```

#### STANDARD-DEPLOY-002: Database Migrations
- **Rule:** Use Alembic for all schema changes
- **Process:**
  1. Create migration: `alembic revision --autogenerate -m "add_soft_delete"`
  2. Review generated SQL
  3. Test on staging
  4. Apply to production with rollback plan
- **Never:** Directly modify production schema

#### STANDARD-DEPLOY-003: Zero-Downtime Deployments
- **Rule:** Use blue-green deployment or rolling updates
- **Process:**
  1. Deploy new version to standby environment
  2. Run health checks
  3. Switch load balancer
  4. Keep old version running for 1 hour (rollback window)

---

### 3.8 FEATURE-SPECIFIC STANDARDS

#### FEATURE: Candidate Screening

**DATA STANDARD:**
- Resume files: PDF (preferred) or DOCX
- Max file size: 5MB
- Text extraction timeout: 30s
- Minimum extractable text: 100 words (else fail with error)

**SCORING STANDARD:**
- Overall score = (skills_match × 0.3) + (experience_match × 0.3) + (education_match × 0.2) + (cultural_fit × 0.2)
- All component scores: 0-100 integer scale
- Scores rounded to nearest integer
- No negative scores

**RECOMMENDATION MAPPING:**
- 90-100: strong_yes
- 75-89: yes
- 60-74: maybe
- 45-59: no
- 0-44: strong_no

**AUDIT REQUIREMENTS:**
- Log input resume hash (SHA-256)
- Log AI prompt version used
- Log raw AI response
- Log parsed scores
- Log user who triggered screening
- Retention: 7 years

---

#### FEATURE: Project Management

**NAMING STANDARD:**
- Project names: 2-200 characters
- Allowed: Alphanumeric, spaces, hyphens, underscores
- Unique within organization (not globally)

**STATUS TRANSITIONS:**
- active → on_hold (any time)
- active → completed (when target_hires met)
- completed → archived (after 90 days)
- on_hold → active (resume project)
- **Forbidden:** archived → any status (permanent)

**DELETION POLICY:**
- Soft delete candidates (mark deleted_at)
- Hard delete positions (CASCADE)
- Hard delete documents (CASCADE, delete files from storage)
- Retain project record for audit (soft delete)

---

#### FEATURE: AI Document Analysis

**SUPPORTED FORMATS:**
- PDF (max 20MB, max 500 pages)
- DOCX (max 10MB)
- TXT (max 1MB)

**EXTRACTION ACCURACY:**
- Target: 95% position title accuracy
- Target: 90% requirement extraction accuracy
- Validation: Manual review of 100 random samples monthly

**CONFIDENCE SCORING:**
- High confidence: >0.8 → Auto-create position (with user approval)
- Medium confidence: 0.5-0.8 → Suggest position (user edits)
- Low confidence: <0.5 → Show raw text (manual entry)

---
