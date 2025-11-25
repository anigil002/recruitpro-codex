# RecruitPro - Requirements Management Document

**Version:** 1.0
**Date:** November 25, 2025
**Status:** Approved
**Author:** RecruitPro Development Team

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Business Requirements](#business-requirements)
3. [Functional Requirements](#functional-requirements)
4. [Non-Functional Requirements](#non-functional-requirements)
5. [Technical Requirements](#technical-requirements)
6. [Security Requirements](#security-requirements)
7. [Integration Requirements](#integration-requirements)
8. [Data Requirements](#data-requirements)
9. [User Interface Requirements](#user-interface-requirements)
10. [Compliance Requirements](#compliance-requirements)
11. [Requirements Prioritization](#requirements-prioritization)
12. [Assumptions and Constraints](#assumptions-and-constraints)

---

## Executive Summary

RecruitPro is an AI-powered Applicant Tracking System (ATS) designed to streamline recruitment operations for staffing agencies, recruitment consultancies, and corporate HR teams. This document outlines all requirements for building RecruitPro from scratch, covering functional capabilities, technical specifications, security measures, and compliance standards.

### Project Objectives

- **Digitize Recruitment Workflows**: Replace manual spreadsheets and emails with a centralized system
- **AI-Enhanced Decision Making**: Leverage AI for CV screening, candidate sourcing, and market intelligence
- **Improve Candidate Quality**: Match candidates to positions with precision using AI scoring
- **Accelerate Time-to-Hire**: Automate repetitive tasks and streamline interview scheduling
- **Provide Market Insights**: Offer salary benchmarking and market research capabilities
- **Ensure Data Security**: Protect sensitive candidate and client information
- **Enable Multi-User Collaboration**: Support recruitment teams with role-based access control

---

## Business Requirements

### BR-001: Multi-Project Management
**Priority:** HIGH
**Description:** System must support managing multiple recruitment projects simultaneously.
**Business Value:** Allows recruiters to handle diverse client engagements concurrently.
**Acceptance Criteria:**
- Users can create unlimited projects
- Each project has unique metadata (client, sector, location, status)
- Projects can be filtered, sorted, and searched
- Projects support status lifecycle: active → on-hold → completed → archived

### BR-002: Position Tracking
**Priority:** HIGH
**Description:** System must track job positions within projects with detailed requirements.
**Business Value:** Enables precise candidate matching and requirement tracking.
**Acceptance Criteria:**
- Multiple positions can be linked to a single project
- Positions include: title, department, location, experience level, description
- Positions support qualifications, responsibilities, and requirements as structured data
- Position status: draft → open → closed

### BR-003: Candidate Pipeline Management
**Priority:** HIGH
**Description:** System must manage candidate progression through recruitment stages.
**Business Value:** Visibility into candidate status and recruitment funnel metrics.
**Acceptance Criteria:**
- Candidates tracked through stages: new → sourced → screening → interviewed → offered → hired/rejected
- Status change history maintained with timestamps and actors
- Bulk status updates supported
- Candidates can be associated with projects and positions

### BR-004: AI-Powered CV Screening
**Priority:** HIGH
**Description:** System must automatically screen CVs against position requirements.
**Business Value:** Reduces manual screening time by 70%, improves candidate quality.
**Acceptance Criteria:**
- Extract key information from resumes (skills, experience, education)
- Generate compliance table showing requirement match
- Provide overall fit assessment (Strong Match / Potential Match / Low Match)
- Identify key strengths and gaps
- Recommend proceed/reject decision with rationale

### BR-005: Market Intelligence
**Priority:** MEDIUM
**Description:** System must provide market research and salary benchmarking.
**Business Value:** Data-driven insights for client proposals and candidate negotiations.
**Acceptance Criteria:**
- Generate market research reports by region and sector
- Provide salary benchmarks by role, seniority, and location
- Include sources and rationale for recommendations
- Cache results for reuse across similar queries

### BR-006: Candidate Sourcing Automation
**Priority:** MEDIUM
**Description:** System must automate candidate discovery from external platforms.
**Business Value:** Expands talent pool beyond inbound applications.
**Acceptance Criteria:**
- Support LinkedIn X-Ray search via Google Custom Search
- Integrate with SmartRecruiters for candidate import
- Generate boolean search strings optimized for platforms
- Track sourcing jobs with progress indicators
- Store sourced profiles with quality scores

### BR-007: Document Management
**Priority:** MEDIUM
**Description:** System must handle uploaded documents (resumes, project briefs, contracts).
**Business Value:** Centralized document repository with access control.
**Acceptance Criteria:**
- Support PDF, DOCX, CSV, TXT file uploads
- Store files securely with access permissions
- Link documents to projects, candidates, or users
- Provide download functionality
- Track upload timestamp and uploader

### BR-008: Interview Scheduling
**Priority:** MEDIUM
**Description:** System must support scheduling and tracking interviews.
**Business Value:** Organizes interview logistics and feedback collection.
**Acceptance Criteria:**
- Schedule interviews with date, time, mode (phone/virtual/in-person)
- Link interviews to candidates and positions
- Record interview notes and feedback
- Display upcoming interviews on dashboard

### BR-009: Activity Auditing
**Priority:** HIGH
**Description:** System must maintain audit trail of all user actions.
**Business Value:** Compliance, accountability, and activity analytics.
**Acceptance Criteria:**
- Log all significant events (logins, project creation, candidate updates, etc.)
- Store actor, timestamp, event type, and affected entities
- Provide activity feed with filtering and pagination
- Support real-time activity streaming

### BR-010: User Access Management
**Priority:** HIGH
**Description:** System must support multiple users with role-based permissions.
**Business Value:** Team collaboration with appropriate access controls.
**Acceptance Criteria:**
- Three role types: recruiter, admin, super_admin
- Role-based access to features and data
- Recruiters access only own projects and candidates
- Admins manage workspace settings and users
- User registration, login, logout, password change

---

## Functional Requirements

### Authentication & Authorization

#### FR-AUTH-001: User Registration
**Priority:** HIGH
**Description:** Users must be able to self-register with email and password.
**Input:** Email, password, name
**Output:** User account created, JWT token issued
**Validation:**
- Email format validation (RFC 5322)
- Email uniqueness check
- Password complexity: min 8 chars, uppercase, lowercase, digit, special char
- Reject common weak passwords
**Related Endpoints:** `POST /api/auth/register`

#### FR-AUTH-002: User Login
**Priority:** HIGH
**Description:** Users must authenticate with email and password.
**Input:** Email, password
**Output:** JWT access token
**Validation:**
- Email exists in system
- Password matches stored hash
- Account not locked/disabled
**Related Endpoints:** `POST /api/auth/login`

#### FR-AUTH-003: Token-Based Session
**Priority:** HIGH
**Description:** System must use JWT tokens for stateless authentication.
**Token Payload:** user_id, role, expiry
**Token Expiry:** Configurable (default 60 minutes, max 1440 minutes)
**Algorithm:** HS256 (HMAC SHA-256)
**Related Components:** `app/utils/security.py`, `app/deps.py`

#### FR-AUTH-004: Password Change
**Priority:** MEDIUM
**Description:** Users must be able to change passwords.
**Input:** Old password, new password
**Output:** Password updated, success confirmation
**Validation:**
- Old password verification
- New password complexity check
- Password history check (prevent reuse)
**Related Endpoints:** `POST /api/auth/change-password`

#### FR-AUTH-005: Role-Based Access Control
**Priority:** HIGH
**Description:** System must enforce permissions based on user roles.
**Roles:**
- **recruiter**: Manage own projects and candidates
- **admin**: Manage workspace, view all users, configure integrations
- **super_admin**: Full system access including database operations
**Enforcement:** Decorator-based route protection, dependency injection checks
**Related Components:** `app/utils/security.py::can_manage_workspace()`

### Project Management

#### FR-PROJ-001: Create Project
**Priority:** HIGH
**Description:** Users must be able to create recruitment projects.
**Input:** Name, client, sector, location_region, summary, priority, tags
**Output:** Project created with unique ID
**Validation:**
- Name required (1-200 chars)
- Client required
- Priority enum: low, medium, high, urgent
- Status defaults to "active"
**Related Endpoints:** `POST /api/projects`
**Related Models:** `Project`

#### FR-PROJ-002: List Projects
**Priority:** HIGH
**Description:** Users must view list of their projects.
**Input:** Page number, limit, filters (status, priority, sector)
**Output:** Paginated project list with metadata
**Filtering:**
- Status: active, on-hold, completed, archived
- Priority: low, medium, high, urgent
- Sector: custom values
**Sorting:** By created_at (DESC default)
**Related Endpoints:** `GET /api/projects`

#### FR-PROJ-003: View Project Details
**Priority:** HIGH
**Description:** Users must view detailed project information.
**Input:** project_id
**Output:** Full project details including positions, candidates, documents
**Included Data:**
- Project metadata
- Position count by status
- Candidate count by status
- Recent candidates
- Uploaded documents
- Activity feed
- Market research status
**Related Endpoints:** `GET /api/projects/{id}`

#### FR-PROJ-004: Update Project
**Priority:** HIGH
**Description:** Users must be able to modify project details.
**Input:** project_id, updated fields
**Output:** Updated project
**Validation:**
- User owns project
- Status transitions valid
- Required fields maintained
**Related Endpoints:** `PUT /api/projects/{id}`

#### FR-PROJ-005: Archive/Delete Project
**Priority:** MEDIUM
**Description:** Users must be able to archive or delete projects.
**Input:** project_id
**Output:** Project status updated or soft-deleted
**Cascade Effects:**
- Positions remain accessible
- Candidates remain in system
- Documents preserved
**Related Endpoints:** `DELETE /api/projects/{id}`

#### FR-PROJ-006: Bulk Project Status Update
**Priority:** LOW
**Description:** Admin users can bulk update project statuses.
**Input:** List of project_ids, new status
**Output:** Count of updated projects
**Validation:**
- Admin role required
- Valid status enum
**Related Endpoints:** `PATCH /api/projects/bulk/lifecycle`

### Position Management

#### FR-POS-001: Create Position
**Priority:** HIGH
**Description:** Users must create positions within projects.
**Input:** project_id, title, department, location, experience, description, qualifications, responsibilities, requirements, openings
**Output:** Position created with unique ID
**Validation:**
- Title + location unique within project
- Openings > 0
- Experience enum: entry, mid, senior, executive
**Related Endpoints:** `POST /api/projects/{project_id}/positions`
**Related Models:** `Position`

#### FR-POS-002: List Positions
**Priority:** HIGH
**Description:** Users must view positions within projects or globally.
**Input:** Optional project_id filter, pagination
**Output:** Paginated position list
**Filtering:**
- Status: draft, open, closed
- Department, location, experience level
**Sorting:** By created_at DESC
**Related Endpoints:** `GET /api/projects/{project_id}/positions`, `GET /api/positions`

#### FR-POS-003: View Position Details
**Priority:** HIGH
**Description:** Users must view detailed position information.
**Input:** position_id
**Output:** Full position details including applicants
**Included Data:**
- Position metadata
- Qualifications list
- Responsibilities list
- Requirements (must-have vs nice-to-have)
- Applicant count
- Linked candidates
**Related Endpoints:** `GET /api/positions/{id}`

#### FR-POS-004: Update Position
**Priority:** HIGH
**Description:** Users must modify position details.
**Input:** position_id, updated fields
**Output:** Updated position
**Validation:**
- User owns parent project
- Title + location uniqueness maintained
**Related Endpoints:** `PUT /api/positions/{id}`

#### FR-POS-005: Delete Position
**Priority:** MEDIUM
**Description:** Users must be able to delete positions.
**Input:** position_id
**Output:** Position deleted
**Cascade Effects:**
- Candidate associations cleared
- Screening results preserved
**Related Endpoints:** `DELETE /api/positions/{id}`

### Candidate Management

#### FR-CAND-001: Create Candidate
**Priority:** HIGH
**Description:** Users must manually add candidates to the system.
**Input:** name, email, phone, source, status, project_id, position_id, resume_url, tags
**Output:** Candidate created with unique ID
**Validation:**
- Email format validation
- Email uniqueness within project (soft)
- Status enum: new, sourced, screening, interviewed, offered, hired, rejected
**Related Endpoints:** `POST /api/candidates`
**Related Models:** `Candidate`

#### FR-CAND-002: List Candidates
**Priority:** HIGH
**Description:** Users must view list of candidates with filtering.
**Input:** Pagination, filters (project, position, status, source, tags)
**Output:** Paginated candidate list
**Filtering:**
- Project ID
- Position ID
- Status (multi-select)
- Source (LinkedIn, Referral, Website, etc.)
- Tags (custom labels)
- Search by name/email
**Sorting:** By created_at DESC
**Related Endpoints:** `GET /api/candidates`

#### FR-CAND-003: View Candidate Profile
**Priority:** HIGH
**Description:** Users must view detailed candidate information.
**Input:** candidate_id
**Output:** Full candidate profile
**Included Data:**
- Personal information (name, email, phone)
- Resume/CV link
- Source and status
- AI screening results (compliance table, strengths, gaps, recommendation)
- Associated project and position
- Tags and ratings
- Status change history
**Related Endpoints:** `GET /api/candidates/{id}`

#### FR-CAND-004: Update Candidate
**Priority:** HIGH
**Description:** Users must modify candidate information.
**Input:** candidate_id, updated fields
**Output:** Updated candidate
**Validation:**
- User has access to candidate's project
- Email uniqueness maintained
**Status Change Tracking:**
- Record old_status, new_status, changed_by, changed_at in `candidate_status_history`
**Related Endpoints:** `PUT /api/candidates/{id}`, `PATCH /api/candidates/{id}`

#### FR-CAND-005: Soft Delete Candidate
**Priority:** MEDIUM
**Description:** Users must be able to delete candidates (soft delete).
**Input:** candidate_id
**Output:** Candidate marked as deleted
**Implementation:**
- Set deleted_at timestamp
- Set deleted_by user_id
- Exclude from normal queries
**Recovery:** Admin can restore by clearing deleted_at
**Related Endpoints:** `DELETE /api/candidates/{id}`

#### FR-CAND-006: Bulk Candidate Operations
**Priority:** MEDIUM
**Description:** Users must perform bulk actions on candidates.
**Supported Actions:**
- Bulk create/update
- Bulk status change
- Bulk tag assignment
**Input:** List of candidate_ids, action type, parameters
**Output:** Count of affected candidates
**Related Endpoints:** `POST /api/candidates/bulk`, `POST /api/candidates/bulk-action`

#### FR-CAND-007: Candidate Import
**Priority:** MEDIUM
**Description:** Users must import candidates from CSV/Excel files.
**Input:** Uploaded file (CSV/XLSX)
**Output:** Import summary (created, updated, errors)
**Mapping:**
- Name → name
- Email → email
- Phone → phone
- Resume URL → resume_url
- Tags → tags (comma-separated)
**Validation:** Email format, required fields
**Related Endpoints:** `POST /api/candidates/import`

#### FR-CAND-008: Candidate Export
**Priority:** MEDIUM
**Description:** Users must export candidates to CSV/Excel.
**Input:** Filters (project, position, status)
**Output:** Downloadable file with candidate data
**Columns:** name, email, phone, source, status, project, position, tags, rating, created_at
**Related Endpoints:** `GET /api/candidates/export`

### AI Features

#### FR-AI-001: CV Screening
**Priority:** HIGH
**Description:** System must automatically screen CVs against position requirements.
**Input:** candidate_id, position_id
**Output:** Detailed screening report
**Report Format (Egis Standard):**
```
Overall Fit: Strong Match / Potential Match / Low Match
Compliance Table:
  | Requirement | Status | Evidence |
  |-------------|--------|----------|
  | 5+ years Python | ✓ Met | 7 years experience at... |
  | AWS certification | ✗ Not Met | No AWS certification mentioned |
Key Strengths:
  - Deep expertise in FastAPI and SQLAlchemy
  - Proven track record in ATS development
Potential Gaps:
  - No cloud certification
  - Limited DevOps experience
Final Recommendation: [Detailed paragraph]
Final Decision: Proceed to technical interview / Suitable for lower role / Reject
```
**Storage:** Save to `screening_runs` table and `candidate.ai_score` JSON field
**Fallback:** Basic text extraction if AI unavailable
**Related Endpoints:** `POST /api/ai/screen-candidate`
**Related Services:** `app/services/gemini.py::screen_cv()`

#### FR-AI-002: Document Analysis
**Priority:** MEDIUM
**Description:** System must extract project/position info from uploaded documents.
**Input:** document_id or file upload
**Output:** Structured data (project name, client, sector, positions list)
**Supported Formats:** PDF, DOCX, CSV, TXT
**Extraction Logic:**
- Identify document type (project brief, RFP, SOW, position description)
- Extract key metadata
- Parse position listings
- Return as JSON schema
**Related Endpoints:** `POST /api/ai/analyze-file`
**Related Services:** `app/services/gemini.py::analyze_file()`

#### FR-AI-003: Job Description Generation
**Priority:** MEDIUM
**Description:** System must generate professional job descriptions.
**Input:** position_title, context (company, sector, seniority)
**Output:** Structured JD with responsibilities, requirements, compensation notes
**Format:**
```
Responsibilities:
  - [Bullet points]
Requirements:
  Core:
    - [Must-have skills/experience]
  Nice-to-Have:
    - [Preferred qualifications]
Compensation:
  - [Salary range guidance]
Experience Level: [Entry/Mid/Senior/Executive]
```
**Related Endpoints:** `POST /api/ai/generate-jd`
**Related Services:** `app/services/gemini.py::generate_job_description()`

#### FR-AI-004: Market Research
**Priority:** MEDIUM
**Description:** System must generate market intelligence reports.
**Input:** region, sector, optional window (time period)
**Output:** Market research report with insights and sources
**Report Sections:**
- Talent availability assessment
- Key trends and challenges
- Comparable projects/companies
- Salary expectations
- Sources (citations)
**Storage:** Save to `project_market_research` table
**Caching:** Reuse recent reports for same region+sector
**Related Endpoints:** `POST /api/research/market-analysis`
**Related Services:** `app/services/gemini.py::generate_market_research()`

#### FR-AI-005: Salary Benchmarking
**Priority:** MEDIUM
**Description:** System must provide salary benchmarks.
**Input:** title, region, sector, seniority, currency
**Output:** Annual salary range (min/mid/max) with rationale
**Adjustment Factors:**
- Seniority level (+/- 30%)
- Region cost of living
- Sector (finance, tech, healthcare, etc.)
**Storage:** Cache in `salary_benchmarks` table
**Reuse:** Return cached results for identical queries within 90 days
**Related Endpoints:** `POST /api/research/salary-benchmark`
**Related Services:** `app/services/gemini.py::generate_salary_benchmark()`

#### FR-AI-006: Candidate Scoring
**Priority:** MEDIUM
**Description:** System must score candidates on multiple dimensions.
**Input:** candidate_id, position_id
**Output:** Multi-dimensional score (0-100 each)
**Dimensions:**
- Technical Fit: Skills match to requirements
- Cultural Alignment: Values, work style compatibility
- Growth Potential: Learning agility, career trajectory
- Overall Match: Weighted average
**Storage:** Save to `candidate.ai_score` JSON field
**Related Services:** `app/services/gemini.py::score_candidate()`

#### FR-AI-007: Outreach Email Generation
**Priority:** LOW
**Description:** System must generate personalized outreach emails.
**Input:** candidate_name, role_title, company_context, template_type
**Output:** Email subject + body
**Templates:**
- Standard outreach
- Executive search
- Technical role
**Personalization:** Include candidate name, role specifics, company value proposition
**Related Endpoints:** `POST /api/ai/generate-email`
**Related Services:** `app/services/gemini.py::generate_outreach_email()`

#### FR-AI-008: Call Script Generation
**Priority:** LOW
**Description:** System must generate recruiter call scripts.
**Input:** candidate_profile, role_details
**Output:** Structured call script
**Script Sections:**
- Introduction
- Motivation probing questions
- Technical/managerial assessment questions
- Objection handling
- Closing statement
**Related Endpoints:** `POST /api/ai/call-script`
**Related Services:** `app/services/gemini.py::generate_call_script()`

#### FR-AI-009: Chatbot Assistant
**Priority:** LOW
**Description:** System must provide conversational AI assistant.
**Input:** user_message, session_id
**Output:** Assistant response with tool suggestions
**Capabilities:**
- Answer recruitment questions
- Suggest market research
- Recommend sourcing strategies
- Provide salary data
**Session Management:** Store conversation history in `chatbot_sessions` and `chatbot_messages`
**Related Endpoints:** `POST /api/chatbot`
**Related Services:** `app/services/gemini.py::generate_chatbot_reply()`

#### FR-AI-010: Boolean Search Generation
**Priority:** LOW
**Description:** System must generate optimized boolean search strings.
**Input:** persona (skills, location, seniority)
**Output:** LinkedIn X-Ray compatible search string
**Format:** Google CSE operators (site:linkedin.com/in/ AND skills OR skills)
**Related Services:** `app/services/gemini.py::build_boolean_search()`

### Candidate Sourcing

#### FR-SRC-001: LinkedIn X-Ray Search
**Priority:** MEDIUM
**Description:** System must search LinkedIn profiles via Google Custom Search.
**Input:** persona, position_id, max_results
**Output:** List of LinkedIn profile URLs with metadata
**Process:**
1. Generate boolean search string
2. Execute Google CSE API query
3. Parse profile URLs and snippets
4. Store in `sourcing_results` table
5. Track job in `sourcing_jobs`
**Related Endpoints:** `POST /api/sourcing/linkedin-xray`
**Related Services:** `app/services/sourcing.py`

#### FR-SRC-002: SmartRecruiters Integration
**Priority:** MEDIUM
**Description:** System must import candidates from SmartRecruiters.
**Input:** company_id, filters, credentials
**Output:** Imported candidate list
**Process:**
1. Authenticate with SmartRecruiters (Playwright)
2. Navigate to candidate list
3. Scrape candidate data (name, email, status, tags)
4. Map to RecruitPro candidate schema
5. Bulk import candidates
**Error Handling:** SmartRecruitersLoginError, SmartRecruitersScrapeError
**Related Endpoints:** `POST /api/sourcing/smartrecruiters-bulk`
**Related Services:** `app/services/smartrecruiters.py`

#### FR-SRC-003: Sourcing Job Tracking
**Priority:** MEDIUM
**Description:** System must track progress of sourcing jobs.
**Input:** sourcing_job_id
**Output:** Job status, progress percentage, found count
**Statuses:** pending → in_progress → completed / failed
**Progress Tracking:** Real-time updates via SSE or polling
**Related Endpoints:** `GET /api/sourcing/{job_id}/status`

#### FR-SRC-004: Sourcing Overview
**Priority:** MEDIUM
**Description:** Users must view all sourcing jobs and results.
**Input:** Optional project_id filter
**Output:** List of sourcing jobs with result counts
**Included Data:**
- Job status and progress
- Platform (LinkedIn, SmartRecruiters)
- Found candidate count
- Quality score distribution
**Related Endpoints:** `GET /api/sourcing/overview`

### Document Management

#### FR-DOC-001: Upload Document
**Priority:** MEDIUM
**Description:** Users must upload files to the system.
**Input:** File (PDF, DOCX, CSV, TXT), scope (project/candidate/user), scope_id
**Output:** Document ID, file URL
**Storage:** Files saved to `/storage/{scope}/{scope_id}/{filename}`
**Validation:**
- File size limit: 50 MB
- MIME type whitelist: application/pdf, application/vnd.openxmlformats-officedocument.wordprocessingml.document, text/csv, text/plain
- Filename sanitization
**Related Endpoints:** `POST /api/documents/upload`
**Related Models:** `Document`, `ProjectDocument`

#### FR-DOC-002: List Documents
**Priority:** MEDIUM
**Description:** Users must view uploaded documents.
**Input:** Optional scope filter (project, candidate)
**Output:** Paginated document list
**Metadata:** filename, mime_type, uploaded_at, uploaded_by
**Related Endpoints:** `GET /api/documents`

#### FR-DOC-003: Download Document
**Priority:** MEDIUM
**Description:** Users must download stored documents.
**Input:** document_id
**Output:** File stream
**Access Control:** User must have access to document's scope
**Related Endpoints:** `GET /api/documents/{id}/download`, `GET /storage/{path}`

#### FR-DOC-004: Delete Document
**Priority:** LOW
**Description:** Users must be able to delete documents.
**Input:** document_id
**Output:** Document deleted, file removed from storage
**Validation:** User owns document or is admin
**Related Endpoints:** `DELETE /api/documents/{id}`

### Interview Management

#### FR-INT-001: Schedule Interview
**Priority:** MEDIUM
**Description:** Users must schedule interviews for candidates.
**Input:** project_id, position_id, candidate_id, scheduled_at, mode, location
**Output:** Interview created with unique ID
**Modes:** phone, in-person, virtual
**Validation:**
- scheduled_at in future
- Candidate and position exist
**Related Endpoints:** `POST /api/interviews`
**Related Models:** `Interview`

#### FR-INT-002: List Interviews
**Priority:** MEDIUM
**Description:** Users must view scheduled interviews.
**Input:** Filters (project, position, candidate, date range)
**Output:** Paginated interview list
**Sorting:** By scheduled_at ASC (upcoming first)
**Related Endpoints:** `GET /api/interviews`

#### FR-INT-003: Update Interview
**Priority:** MEDIUM
**Description:** Users must modify interview details and add feedback.
**Input:** interview_id, updated fields (scheduled_at, location, notes, feedback)
**Output:** Updated interview
**Audit:** Record updated_by and updated_at
**Related Endpoints:** `PUT /api/interviews/{id}`

#### FR-INT-004: Cancel Interview
**Priority:** LOW
**Description:** Users must be able to cancel interviews.
**Input:** interview_id
**Output:** Interview deleted
**Related Endpoints:** `DELETE /api/interviews/{id}`

### Activity & Reporting

#### FR-ACT-001: Activity Logging
**Priority:** HIGH
**Description:** System must log all significant user actions.
**Logged Events:**
- Authentication: login, logout, user_registered, password_changed
- Projects: project_created, project_updated, project_archived
- Positions: position_created, position_updated, position_deleted
- Candidates: candidate_added, candidate_updated, candidate_status_changed, candidate_deleted
- Interviews: interview_scheduled, interview_updated
- AI: ai_screening, ai_jd_generated, ai_sourcing, ai_market_research
- Documents: document_uploaded, document_deleted
**Activity Schema:**
- actor_type: user, system, ai
- actor_id: user_id or system identifier
- event_type: enum
- message: human-readable description
- project_id, position_id, candidate_id: optional context
- created_at: timestamp
**Related Endpoints:** `GET /api/activity`
**Related Models:** `ActivityFeed`

#### FR-ACT-002: Activity Feed Display
**Priority:** MEDIUM
**Description:** Users must view recent activity feed.
**Input:** Pagination, filters (actor, event_type, project, date range)
**Output:** Paginated activity list
**Sorting:** By created_at DESC
**Related Endpoints:** `GET /api/activity`

#### FR-ACT-003: Real-Time Activity Stream
**Priority:** LOW
**Description:** System must support real-time activity updates.
**Protocol:** Server-Sent Events (SSE)
**Endpoint:** `GET /api/activity/stream`
**Events:** JSON payloads pushed to connected clients
**Use Case:** Dashboard live updates

#### FR-REP-001: Dashboard Statistics
**Priority:** MEDIUM
**Description:** System must provide dashboard analytics.
**Input:** Optional date range filter
**Output:** Summary statistics
**Metrics:**
- Total projects (by status)
- Total positions (by status)
- Total candidates (by status)
- Active sourcing jobs
- Recent activity count
- Upcoming interviews
**Related Endpoints:** `GET /api/activity/dashboard/stats`

#### FR-REP-002: Analytics Overview
**Priority:** LOW
**Description:** System must provide detailed analytics.
**Metrics:**
- Time-to-hire average
- Source effectiveness (candidates per source)
- Conversion rates (stage to stage)
- AI screening accuracy
- User activity breakdown
**Related Endpoints:** `GET /api/reporting/overview`

### Administration

#### FR-ADM-001: User Management
**Priority:** HIGH
**Description:** Admin users must manage other users.
**Capabilities:**
- List all users
- Change user roles
- View user activity
- Deactivate users (future)
**Related Endpoints:** `GET /api/admin/users`, `POST /api/admin/users/{id}/role`
**Related Models:** `User`

#### FR-ADM-002: Integration Configuration
**Priority:** HIGH
**Description:** Admin users must configure external integrations.
**Integrations:**
- Gemini API: API key
- Google Custom Search: API key + CSE ID
- SmartRecruiters: Email + password
**Storage:** Encrypted in `integration_credentials` table
**Related Endpoints:** `GET /api/settings`, `POST /api/settings`
**Related Models:** `IntegrationCredential`

#### FR-ADM-003: Feature Flags
**Priority:** LOW
**Description:** Admin users must toggle advanced features.
**Features:**
- AI screening enabled/disabled
- Chatbot enabled/disabled
- Sourcing enabled/disabled
- Market research enabled/disabled
**Storage:** `advanced_features_config` table
**Related Endpoints:** `GET /api/admin/advanced/features`, `PUT /api/admin/advanced/features/{key}`

#### FR-ADM-004: Bulk Data Migration
**Priority:** LOW
**Description:** Admin users must import data from JSON files.
**Input:** JSON file with projects, positions, candidates
**Output:** Import summary (created/updated/errors)
**Validation:** Schema validation, referential integrity
**Logging:** Track in `admin_migration_logs`
**Related Endpoints:** `POST /api/admin/migrate-from-json`

#### FR-ADM-005: System Health Monitoring
**Priority:** MEDIUM
**Description:** System must expose health check endpoint.
**Checks:**
- Database connectivity
- Background queue status
- Redis/RQ status (if configured)
- Gemini API configuration
**Response:** JSON with status (healthy/degraded/unhealthy) and component details
**Related Endpoints:** `GET /api/health`

#### FR-ADM-006: Version Information
**Priority:** LOW
**Description:** System must expose version information.
**Output:** Application version, environment, build timestamp
**Related Endpoints:** `GET /api/version`

---

## Non-Functional Requirements

### Performance Requirements

#### NFR-PERF-001: Response Time
**Priority:** HIGH
**Requirement:** 95% of API requests must complete within 2 seconds under normal load.
**Exceptions:** AI operations (screening, sourcing) may take up to 30 seconds.
**Measurement:** Prometheus metrics, p95 latency

#### NFR-PERF-002: Concurrent Users
**Priority:** MEDIUM
**Requirement:** System must support 100 concurrent users without performance degradation.
**Test Scenario:** 100 users performing mixed operations (CRUD, searches, AI requests)
**Resource Limits:** 4 CPU cores, 8 GB RAM

#### NFR-PERF-003: Database Query Performance
**Priority:** HIGH
**Requirement:** 95% of database queries must complete within 500ms.
**Optimization:** Proper indexing on foreign keys, email, status fields
**Monitoring:** SQLAlchemy query logging, slow query alerts

#### NFR-PERF-004: File Upload Speed
**Priority:** MEDIUM
**Requirement:** Document uploads must process at minimum 1 MB/second.
**Max File Size:** 50 MB
**Streaming:** Use chunked upload for files > 10 MB

#### NFR-PERF-005: AI Request Latency
**Priority:** MEDIUM
**Requirement:** AI screening must complete within 30 seconds for 90% of requests.
**Timeout:** 30 second timeout on Gemini API calls
**Fallback:** Return heuristic results if timeout occurs

### Scalability Requirements

#### NFR-SCAL-001: Database Scalability
**Priority:** HIGH
**Requirement:** System must support databases with 1M+ candidates, 10K+ projects.
**Solution:** PostgreSQL with proper indexing, query optimization, pagination

#### NFR-SCAL-002: Horizontal Scalability
**Priority:** MEDIUM
**Requirement:** System must support horizontal scaling via load balancers.
**Stateless Design:** JWT-based auth, no server-side sessions
**Shared Storage:** Centralized file storage (S3, NFS)

#### NFR-SCAL-003: Background Job Scalability
**Priority:** MEDIUM
**Requirement:** System must handle 1000+ queued background jobs.
**Solution:** Redis + RQ with multiple worker processes
**Priority Queues:** High priority for user-initiated AI requests

### Reliability Requirements

#### NFR-REL-001: Uptime
**Priority:** HIGH
**Requirement:** System must maintain 99.5% uptime (SLA: 3.6 hours downtime/month).
**Monitoring:** Uptime monitoring, health check endpoints
**Alerting:** Sentry for error tracking, email alerts

#### NFR-REL-002: Data Durability
**Priority:** HIGH
**Requirement:** Zero data loss for committed transactions.
**Solution:** PostgreSQL with WAL, daily backups, point-in-time recovery
**Backup Retention:** 30 days minimum

#### NFR-REL-003: Graceful Degradation
**Priority:** HIGH
**Requirement:** System must remain functional when AI services unavailable.
**Fallback Logic:** Return deterministic results for all AI features
**User Notification:** Display warning when AI unavailable

#### NFR-REL-004: Error Recovery
**Priority:** MEDIUM
**Requirement:** Failed background jobs must be retryable.
**Retry Logic:** Exponential backoff (2s, 4s, 8s, 16s)
**Max Retries:** 4 attempts before marking as failed
**Error Logging:** Store error message in `ai_jobs.error` field

### Usability Requirements

#### NFR-USE-001: User Interface Responsiveness
**Priority:** HIGH
**Requirement:** UI must be responsive across desktop, tablet, mobile devices.
**Framework:** Tailwind CSS with mobile-first approach
**Breakpoints:** sm (640px), md (768px), lg (1024px), xl (1280px)

#### NFR-USE-002: Accessibility
**Priority:** MEDIUM
**Requirement:** System must meet WCAG 2.1 Level AA standards.
**Features:**
- Keyboard navigation
- Screen reader compatibility
- Sufficient color contrast
- Alt text for images

#### NFR-USE-003: Browser Compatibility
**Priority:** MEDIUM
**Requirement:** System must support modern browsers.
**Supported:** Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
**Not Supported:** Internet Explorer

#### NFR-USE-004: Error Messages
**Priority:** MEDIUM
**Requirement:** Error messages must be clear and actionable.
**Format:** User-friendly message + error code + suggested action
**Example:** "Invalid email format. Please use format: name@example.com"

### Maintainability Requirements

#### NFR-MAIN-001: Code Quality
**Priority:** MEDIUM
**Requirement:** Codebase must maintain quality standards.
**Linting:** Ruff for Python, ESLint for JavaScript
**Formatting:** Black for Python, Prettier for JavaScript
**Type Checking:** Pydantic for runtime validation

#### NFR-MAIN-002: Test Coverage
**Priority:** MEDIUM
**Requirement:** Maintain 70%+ test coverage for critical paths.
**Framework:** pytest with coverage plugin
**Critical Paths:** Authentication, CRUD operations, AI screening

#### NFR-MAIN-003: Documentation
**Priority:** MEDIUM
**Requirement:** All public APIs must be documented.
**Format:** OpenAPI/Swagger auto-generated from FastAPI
**Access:** `/docs` (Swagger UI), `/redoc` (ReDoc)

#### NFR-MAIN-004: Logging
**Priority:** HIGH
**Requirement:** System must maintain comprehensive logs.
**Levels:** DEBUG (development), INFO (production), ERROR (always)
**Structured:** JSON format for log aggregation
**Retention:** 30 days minimum

---

## Technical Requirements

### TR-001: Programming Language
**Backend:** Python 3.11+
**Frontend:** JavaScript ES6+
**Rationale:** Python for rapid development, strong AI/ML ecosystem

### TR-002: Web Framework
**Backend:** FastAPI 0.111.0+
**Rationale:** High performance, automatic API documentation, async support

### TR-003: Database
**Development:** SQLite 3.x
**Production:** PostgreSQL 14+
**ORM:** SQLAlchemy 2.0+
**Rationale:** SQLite for simplicity, PostgreSQL for production reliability

### TR-004: Authentication
**Mechanism:** JWT (JSON Web Tokens)
**Algorithm:** HS256
**Library:** python-jose 3.3.0+
**Password Hashing:** bcrypt via passlib 1.7.4+

### TR-005: AI Integration
**Provider:** Google Gemini API
**Model:** gemini-2.0-flash-lite
**HTTP Client:** httpx 0.27.0+
**Retry Logic:** tenacity library

### TR-006: Background Jobs
**Production:** Redis 5.0+ + RQ 1.16.0+
**Development:** In-memory thread-based queue
**Rationale:** RQ for simplicity, reliability

### TR-007: Frontend Framework
**Templating:** Jinja2 3.1.3+
**CSS:** Tailwind CSS 3.4.0+
**Build Tool:** PostCSS 8.4.32+
**Rationale:** Minimal JavaScript, fast rendering

### TR-008: Desktop Application
**Framework:** Electron 29.1.0+
**Build:** electron-builder 24.9.1+
**Backend Bundling:** Python + Uvicorn embedded

### TR-009: File Storage
**Development:** Local filesystem (`/storage`)
**Production:** S3-compatible object storage (future)
**Supported Formats:** PDF, DOCX, CSV, TXT

### TR-010: Deployment
**ASGI Server:** Uvicorn 0.30.0+
**Process Manager:** systemd (Linux) or equivalent
**Reverse Proxy:** Nginx recommended
**Containerization:** Docker support (optional)

---

## Security Requirements

### SR-001: Password Security
**Hashing:** PBKDF2-SHA256 via passlib
**Complexity:** Min 8 chars, uppercase, lowercase, digit, special char
**Storage:** Never store plaintext passwords
**History:** Prevent password reuse (last 5 passwords)

### SR-002: Authentication Security
**Token Expiry:** Configurable (default 60 min, max 1440 min)
**Token Rotation:** New token on password change
**Session Invalidation:** Logout clears client-side token
**Brute Force Protection:** Rate limiting on login endpoint (5 attempts/minute)

### SR-003: Authorization Security
**RBAC Enforcement:** Role-based access on all protected endpoints
**Resource Ownership:** Users can only access own projects/candidates
**Admin Verification:** Admin endpoints verify `can_manage_workspace()`
**Token Validation:** Verify signature, expiry, user existence

### SR-004: Data Encryption
**In Transit:** HTTPS only in production (TLS 1.2+)
**At Rest:** Encrypt sensitive fields (integration credentials)
**Encryption Algorithm:** AES-256-GCM via cryptography library
**Key Management:** Environment variable or secure key store

### SR-005: Input Validation
**SQL Injection:** Use parameterized queries (SQLAlchemy ORM)
**XSS Prevention:** Escape output in templates (Jinja2 auto-escape)
**File Upload Validation:** MIME type whitelist, size limit, sanitization
**Email Validation:** RFC 5322 format check

### SR-006: API Security
**CORS:** Whitelist allowed origins
**CSRF Protection:** Not applicable (stateless JWT)
**Rate Limiting:** slowapi middleware (100 requests/minute per IP)
**Security Headers:** HSTS, X-Frame-Options, X-Content-Type-Options, CSP

### SR-007: Audit Trail
**Activity Logging:** All user actions logged to `activity_feed`
**Sensitive Operations:** Password changes, role changes, data deletions
**Retention:** Activity logs retained for 1 year minimum
**Immutability:** Activity records cannot be deleted or modified

### SR-008: Vulnerability Management
**Dependency Scanning:** Regular updates to dependencies
**Error Handling:** No sensitive data in error messages
**Monitoring:** Sentry for error tracking and alerting
**Incident Response:** Security incident playbook (TBD)

---

## Integration Requirements

### IR-001: Google Gemini API
**Purpose:** AI-powered CV screening, JD generation, market research
**Authentication:** API key (encrypted storage)
**Endpoint:** https://generativelanguage.googleapis.com/v1beta
**Rate Limits:** As per Google's terms (handle 429 responses)
**Fallback:** Heuristic-based logic when API unavailable

### IR-002: Google Custom Search API
**Purpose:** LinkedIn X-Ray candidate sourcing
**Authentication:** API key + Custom Search Engine ID
**Rate Limits:** 100 queries/day (free tier)
**Fallback:** Return empty results with user notification

### IR-003: SmartRecruiters
**Purpose:** Bulk candidate import
**Authentication:** Email + password (Playwright automation)
**Method:** Web scraping via browser automation
**Rate Limits:** Respectful scraping (delays between requests)
**Error Handling:** Login failures, CAPTCHA detection

### IR-004: Future Integrations (Planned)
- LinkedIn Recruiter API (official)
- Indeed API
- Glassdoor API
- Email service (SendGrid, AWS SES)
- Calendar integration (Google Calendar, Outlook)
- Video conferencing (Zoom, Teams)

---

## Data Requirements

### DR-001: Data Model
**Entities:** 15+ tables (see ER diagram in traceability matrix)
**Relationships:**
- Projects 1:N Positions
- Positions 1:N Candidates
- Users 1:N Projects/Candidates/Documents
- Candidates 1:N ScreeningRuns, StatusHistory

### DR-002: Data Retention
**Active Data:** Retained indefinitely
**Soft-Deleted Candidates:** Retain for 1 year, then hard delete
**Activity Logs:** Retain for 1 year
**AI Job Logs:** Retain for 90 days
**Documents:** Retain while associated entity exists

### DR-003: Data Privacy
**PII Fields:** name, email, phone, resume content
**Access Control:** Users access only own data (except admins)
**Data Deletion:** Soft delete candidates (GDPR right to erasure)
**Data Export:** Candidate export to CSV (GDPR data portability)

### DR-004: Data Backup
**Frequency:** Daily automated backups
**Retention:** 30 days rolling
**Storage:** Off-site backup location
**Recovery:** Point-in-time recovery within 1 hour

### DR-005: Data Migration
**Import:** Support CSV, JSON bulk import
**Export:** CSV export for candidates, projects, positions
**Schema Versioning:** Alembic migrations for schema changes

---

## User Interface Requirements

### UIR-001: Layout
**Structure:** Top navigation bar, sidebar (optional), main content area
**Navigation:** Persistent menu with dashboard, projects, candidates, settings
**Breadcrumbs:** Show current location in hierarchy

### UIR-002: Dashboard
**Widgets:**
- Statistics cards (projects, positions, candidates)
- Recent projects table
- Open positions table
- Candidate pipeline chart
- Activity feed
- Upcoming interviews

### UIR-003: Forms
**Validation:** Real-time client-side validation with server-side verification
**Error Display:** Inline error messages below fields
**Required Fields:** Visual indicator (asterisk or label)
**Submit Feedback:** Loading spinner, success/error toasts

### UIR-004: Tables
**Features:** Sorting, filtering, pagination
**Pagination:** Client-side or server-side (for large datasets)
**Actions:** Row-level actions (edit, delete, view)
**Bulk Actions:** Multi-select with bulk operations

### UIR-005: Modals
**Usage:** Forms, confirmations, detailed views
**Behavior:** Dismissible via X button, ESC key, or outside click
**Stacking:** Support multiple modal layers

### UIR-006: Notifications
**Types:** Success, error, warning, info
**Display:** Toast notifications (auto-dismiss after 5 seconds)
**Positioning:** Top-right corner

### UIR-007: Loading States
**Indicators:** Spinners for async operations
**Skeleton Screens:** For content loading (optional)
**Progress Bars:** For long-running operations (sourcing, imports)

---

## Compliance Requirements

### CR-001: GDPR Compliance
**Right to Access:** Candidates can request their data (export feature)
**Right to Erasure:** Soft delete candidates with purge after retention period
**Data Minimization:** Collect only necessary candidate information
**Consent:** Document candidate consent for data processing (future)
**Data Protection Officer:** Designate DPO for EU deployments

### CR-002: Data Protection
**Encryption:** TLS for data in transit, AES-256 for sensitive fields
**Access Logs:** Maintain audit trail of data access
**Data Classification:** PII clearly identified and protected
**Breach Notification:** Incident response plan for data breaches

### CR-003: Industry Standards
**OWASP Top 10:** Address all OWASP vulnerabilities
**NIST Cybersecurity Framework:** Align security practices
**ISO 27001:** Information security management (future certification)

### CR-004: Accessibility
**WCAG 2.1 Level AA:** Meet accessibility standards
**Screen Readers:** ARIA labels for assistive technologies
**Keyboard Navigation:** Full keyboard accessibility

---

## Requirements Prioritization

### MoSCoW Method

#### Must Have (MVP)
- Authentication & authorization
- Project, position, candidate CRUD
- AI CV screening
- Document upload
- Activity logging
- Dashboard

#### Should Have (Phase 2)
- Market research & salary benchmarking
- Candidate sourcing (LinkedIn, SmartRecruiters)
- Interview scheduling
- Bulk operations
- Real-time activity stream

#### Could Have (Phase 3)
- Chatbot assistant
- Advanced analytics
- Email/calendar integration
- Mobile app
- Vector search

#### Won't Have (Deferred)
- Video interviewing
- Background checks integration
- Offer letter generation
- Onboarding workflows

---

## Assumptions and Constraints

### Assumptions

1. **Users have modern browsers:** Chrome, Firefox, Safari, Edge (latest 2 versions)
2. **Internet connectivity:** System requires internet for AI features
3. **English language:** Initial release supports English only
4. **Single tenant:** Each deployment serves one organization
5. **Gemini API availability:** Google Gemini API remains available and affordable
6. **User training:** Users receive basic training on ATS concepts

### Constraints

1. **Budget:** Limited budget for third-party services (use free tiers where possible)
2. **Timeline:** MVP delivery in 12 weeks
3. **Team size:** 2-3 developers
4. **Infrastructure:** Deploy on single server initially (horizontal scaling later)
5. **AI costs:** Gemini API costs must stay under $500/month
6. **Storage:** Local filesystem storage initially (S3 migration later)
7. **Compliance:** GDPR compliance required for EU customers

### Dependencies

1. **Google Gemini API:** Core AI features depend on API availability
2. **Google Custom Search:** LinkedIn sourcing depends on CSE
3. **SmartRecruiters:** Candidate import depends on platform stability
4. **PostgreSQL:** Production deployment requires PostgreSQL
5. **Redis:** Background job processing requires Redis (optional in dev)

---

## Change Management

### Change Request Process

1. **Submission:** Stakeholder submits change request with justification
2. **Review:** Development team reviews impact, effort, priority
3. **Approval:** Product owner approves/rejects
4. **Implementation:** Assign to sprint, implement, test
5. **Documentation:** Update requirements document

### Requirements Versioning

- **Version 1.0:** Initial MVP requirements (this document)
- **Version 1.1:** Post-MVP enhancements
- **Version 2.0:** Major feature additions (chatbot, analytics)

### Traceability

All requirements linked to:
- Implementation (code files)
- Test cases
- User stories
- API endpoints

See TRACEABILITY_MATRIX.md for complete mapping.

---

**Document Approval:**

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Product Owner | [Name] | ___________ | ________ |
| Lead Developer | [Name] | ___________ | ________ |
| QA Lead | [Name] | ___________ | ________ |

---

**End of Requirements Management Document**
