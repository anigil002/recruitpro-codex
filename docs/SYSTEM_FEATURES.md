# RecruitPro - System Features Documentation

**Version:** 1.0
**Date:** November 25, 2025
**Purpose:** Complete catalog of all RecruitPro features

---

## Core Features Summary

RecruitPro provides **67 distinct features** across 10 functional areas:

1. **User Management** (8 features)
2. **Project Management** (9 features)
3. **Position Management** (7 features)
4. **Candidate Management** (12 features)
5. **AI-Powered Features** (11 features)
6. **Candidate Sourcing** (6 features)
7. **Interview Management** (5 features)
8. **Document Management** (4 features)
9. **Activity & Reporting** (3 features)
10. **Admin & Configuration** (2 features)

---

## 1. User Management Features

### 1.1 User Registration
- **Description**: Self-service user account creation
- **Access**: Public (no authentication required)
- **Endpoint**: `POST /api/auth/register`
- **Inputs**: Email, password, full name
- **Validation**:
  - Email format (RFC 5322)
  - Email uniqueness
  - Password complexity (8+ chars, uppercase, lowercase, digit, special char)
  - Reject common weak passwords
  - Block sequential patterns (123, abc)
- **Output**: User account created, JWT token issued
- **Default Role**: recruiter

### 1.2 User Login
- **Description**: Email/password authentication
- **Access**: Public
- **Endpoint**: `POST /api/auth/login`
- **Inputs**: Email (username), password
- **Process**:
  1. Validate email exists
  2. Verify password hash
  3. Generate JWT token (HS256)
  4. Log activity (login event)
- **Token Expiry**: Configurable (default 60 min, max 1440 min)
- **Output**: JWT access token

### 1.3 User Logout
- **Description**: Logout activity logging
- **Access**: Authenticated users
- **Endpoint**: `POST /api/auth/logout`
- **Process**: Logs logout event to activity feed
- **Note**: JWT tokens remain valid until expiry (stateless)

### 1.4 Password Change
- **Description**: Update user password
- **Access**: Authenticated users
- **Endpoint**: `POST /api/auth/change-password`
- **Inputs**: Old password, new password
- **Validation**:
  - Old password verification
  - New password complexity check
  - Password history check (prevent reuse of last 5)
- **Process**:
  1. Verify old password
  2. Hash new password (PBKDF2-SHA256)
  3. Store in password_history table
  4. Update user record
  5. Log activity

### 1.5 Role-Based Access Control
- **Description**: Three-tier permission system
- **Roles**:
  - **recruiter**: Manage own projects/candidates
  - **admin**: Workspace management, user role assignment
  - **super_admin**: Full system access
- **Enforcement**: Dependency injection (`get_current_user`, `require_admin`)

### 1.6 User Profile Management
- **Description**: View and update user settings
- **Fields**: Name, email (immutable), role, settings (JSON)
- **Settings**: Theme preferences, notification settings, default filters

### 1.7 User List (Admin)
- **Description**: View all workspace users
- **Access**: Admin, super_admin
- **Endpoint**: `GET /api/admin/users`
- **Output**: Paginated user list with roles and activity

### 1.8 Role Assignment (Admin)
- **Description**: Change user roles
- **Access**: Admin, super_admin
- **Endpoint**: `POST /api/admin/users/{id}/role`
- **Inputs**: user_id, new_role
- **Validation**: Cannot demote own account

---

## 2. Project Management Features

### 2.1 Create Project
- **Description**: Create new recruitment project
- **Access**: All authenticated users
- **Endpoint**: `POST /api/projects`
- **Inputs**:
  - name (required, 1-200 chars)
  - client (required)
  - sector (infrastructure, aviation, rail, energy, buildings, healthcare)
  - location_region (GCC, Middle East, North America, etc.)
  - summary (text)
  - priority (low, medium, high, urgent)
  - tags (array)
  - target_hires (integer)
  - team_members (JSON array)
- **Defaults**:
  - status: active
  - created_by: current_user.user_id
  - hires_count: 0
- **Activity Log**: project_created event

### 2.2 List Projects
- **Description**: View user's projects with filtering
- **Access**: Authenticated users
- **Endpoint**: `GET /api/projects`
- **Query Parameters**:
  - page (default 1)
  - limit (default 20, max 100)
  - status (active, on-hold, completed, archived)
  - priority (low, medium, high, urgent)
  - sector
  - search (name, client)
- **Sorting**: created_at DESC
- **Permissions**: Users see only own projects (unless admin)

### 2.3 View Project Details
- **Description**: Detailed project information
- **Access**: Project owner or admin
- **Endpoint**: `GET /api/projects/{id}`
- **Output**:
  - Project metadata
  - Position count by status
  - Candidate count by status
  - Recent candidates (last 10)
  - Uploaded documents
  - Activity feed (project-specific)
  - Market research status

### 2.4 Update Project
- **Description**: Modify project details
- **Access**: Project owner or admin
- **Endpoint**: `PUT /api/projects/{id}`
- **Updatable Fields**: All except project_id, created_by, created_at
- **Validation**: Status transitions valid
- **Activity Log**: project_updated event

### 2.5 Archive/Delete Project
- **Description**: Soft-delete or archive project
- **Access**: Project owner or admin
- **Endpoint**: `DELETE /api/projects/{id}`
- **Process**:
  - Update status to "archived"
  - Positions remain accessible
  - Candidates remain in system
  - Documents preserved
- **Activity Log**: project_archived event

### 2.6 Bulk Status Update
- **Description**: Update multiple project statuses
- **Access**: Admin only
- **Endpoint**: `PATCH /api/projects/bulk/lifecycle`
- **Inputs**: project_ids (array), new_status
- **Use Case**: Quarterly project cleanup

### 2.7 Project Dashboard
- **Description**: Single-page project overview
- **Access**: Project owner or admin
- **Route**: `/project-overview?project_id={id}`
- **Components**:
  - Project summary card
  - Open positions table
  - Candidate pipeline chart
  - Recent candidates list
  - Documents section
  - Activity feed

### 2.8 Project Positions View
- **Description**: All positions in project
- **Access**: Project owner or admin
- **Route**: `/project-positions?project_id={id}`
- **Display**: Position cards with status badges

### 2.9 Project Documents
- **Description**: Upload/download project files
- **Access**: Project owner or admin
- **Supported Formats**: PDF, DOCX, CSV, TXT
- **Max Size**: 50 MB
- **Storage**: `/storage/projects/{project_id}/`

---

## 3. Position Management Features

### 3.1 Create Position
- **Description**: Define job opening within project
- **Access**: Project owner or admin
- **Endpoint**: `POST /api/projects/{project_id}/positions`
- **Inputs**:
  - title (required)
  - department
  - location (required)
  - experience (entry, mid, senior, executive)
  - description (text)
  - qualifications (JSON array)
  - responsibilities (JSON array)
  - requirements (JSON array - must-have)
  - openings (integer, default 1)
- **Validation**: Unique (project_id, title, location)
- **Defaults**:
  - status: draft
  - applicants_count: 0
- **Activity Log**: position_created event

### 3.2 List Positions
- **Description**: View positions across projects or within project
- **Access**: Authenticated users
- **Endpoints**:
  - `GET /api/positions` (all positions)
  - `GET /api/projects/{id}/positions` (project-specific)
- **Filters**:
  - status (draft, open, closed)
  - department
  - location
  - experience
  - project_id
- **Sorting**: created_at DESC

### 3.3 View Position Details
- **Description**: Full position information
- **Access**: Project owner or admin
- **Endpoint**: `GET /api/positions/{id}`
- **Output**:
  - Position metadata
  - Qualifications list
  - Responsibilities list
  - Requirements (must-have vs nice-to-have)
  - Applicant count
  - Linked candidates

### 3.4 Update Position
- **Description**: Modify position details
- **Access**: Project owner or admin
- **Endpoint**: `PUT /api/positions/{id}`
- **Validation**: Title + location uniqueness maintained
- **Activity Log**: position_updated event

### 3.5 Delete Position
- **Description**: Remove position from project
- **Access**: Project owner or admin
- **Endpoint**: `DELETE /api/positions/{id}`
- **Cascade**: Candidate associations cleared, screening results preserved
- **Activity Log**: position_deleted event

### 3.6 Generate Job Description (AI)
- **Description**: AI-powered JD creation
- **Access**: Project owner or admin
- **Endpoint**: `POST /api/ai/generate-jd`
- **Inputs**: title, context (project, sector, seniority)
- **Output**: Structured JD (responsibilities, requirements, compensation)
- **Model**: Gemini 2.5 Flash Lite
- **Fallback**: Template-based generation

### 3.7 Position Status Management
- **Description**: Track position lifecycle
- **States**: draft → open → closed
- **Rules**:
  - draft: Initial creation, not visible to candidates
  - open: Active recruiting, accepts applicants
  - closed: No longer accepting applicants

---

## 4. Candidate Management Features

### 4.1 Create Candidate
- **Description**: Manually add candidate to system
- **Access**: All authenticated users
- **Endpoint**: `POST /api/candidates`
- **Inputs**:
  - name (required)
  - email (required, unique check)
  - phone
  - source (LinkedIn, Referral, Website, Direct Apply, etc.)
  - status (new, sourced, screening, interviewed, offered, hired, rejected)
  - project_id (optional)
  - position_id (optional)
  - resume_url
  - tags (JSON array)
  - rating (1-5)
- **Defaults**:
  - candidate_id: generated UUID
  - created_by: current_user.user_id
  - status: new
- **Activity Log**: candidate_added event

### 4.2 List Candidates
- **Description**: View candidates with advanced filtering
- **Access**: Authenticated users
- **Endpoint**: `GET /api/candidates`
- **Filters**:
  - project_id
  - position_id
  - status (multi-select)
  - source
  - tags
  - rating (min/max)
  - search (name, email)
  - created_by
- **Pagination**: page, limit
- **Sorting**: created_at DESC
- **Permissions**: Users see own candidates (unless admin)

### 4.3 View Candidate Profile
- **Description**: Comprehensive candidate details
- **Access**: Candidate owner or admin
- **Endpoint**: `GET /api/candidates/{id}`
- **Output**:
  - Personal information
  - Resume/CV link
  - Source and status
  - AI screening results (ai_score JSON)
  - Associated project and position
  - Tags and ratings
  - Status change history
  - Screening runs

### 4.4 Update Candidate
- **Description**: Modify candidate information
- **Access**: Candidate owner or admin
- **Endpoints**:
  - `PUT /api/candidates/{id}` (full update)
  - `PATCH /api/candidates/{id}` (partial update)
- **Status Change Tracking**:
  - If status changed, record in candidate_status_history
  - Track old_status, new_status, changed_by, changed_at
- **Activity Log**: candidate_updated, candidate_status_changed events

### 4.5 Soft Delete Candidate
- **Description**: Mark candidate as deleted (recoverable)
- **Access**: Candidate owner or admin
- **Endpoint**: `DELETE /api/candidates/{id}`
- **Process**:
  - Set deleted_at timestamp
  - Set deleted_by user_id
  - Exclude from normal queries
- **Recovery**: Admin can restore by clearing deleted_at
- **Activity Log**: candidate_deleted event

### 4.6 Bulk Create/Update Candidates
- **Description**: Mass candidate operations
- **Access**: Authenticated users
- **Endpoint**: `POST /api/candidates/bulk`
- **Inputs**: Array of candidate objects
- **Process**:
  - Validate each candidate
  - Create or update based on email uniqueness
  - Track success/error counts
- **Output**: {created: N, updated: M, errors: [...]}

### 4.7 Bulk Action (Status/Tags)
- **Description**: Apply changes to multiple candidates
- **Access**: Authenticated users
- **Endpoint**: `POST /api/candidates/bulk-action`
- **Actions**:
  - status_change: Update status for candidate_ids
  - add_tags: Append tags to candidates
  - remove_tags: Remove tags from candidates
  - assign_project: Link to project
  - assign_position: Link to position
- **Output**: Count of affected candidates

### 4.8 Import Candidates (CSV/Excel)
- **Description**: Bulk import from spreadsheet
- **Access**: Authenticated users
- **Endpoint**: `POST /api/candidates/import`
- **Supported Formats**: CSV, XLSX
- **Mapping**:
  - Name → name
  - Email → email
  - Phone → phone
  - Resume URL → resume_url
  - Tags → tags (comma-separated)
- **Validation**: Email format, required fields
- **Output**: Import summary (created, updated, errors)

### 4.9 Export Candidates (CSV/Excel)
- **Description**: Download candidate data
- **Access**: Authenticated users
- **Endpoint**: `GET /api/candidates/export?format=csv`
- **Formats**: CSV, XLSX (if openpyxl installed)
- **Filters**: Apply same filters as list endpoint
- **Columns**: name, email, phone, source, status, project, position, tags, rating, created_at

### 4.10 Candidate Status History
- **Description**: Audit trail of status changes
- **Model**: candidate_status_history table
- **Fields**:
  - history_id (PK)
  - candidate_id (FK)
  - old_status, new_status
  - changed_by (FK users)
  - changed_at (timestamp)
- **Access**: Via candidate profile view

### 4.11 Candidate Tagging
- **Description**: Custom labels for segmentation
- **Format**: JSON array of strings
- **Use Cases**:
  - "vip", "urgent", "relocatable"
  - "technical-expert", "leadership-ready"
  - "gcc-experience", "aviation-specialist"
- **Operations**: Add tags, remove tags, filter by tags

### 4.12 Candidate Rating
- **Description**: Manual quality assessment
- **Scale**: 1-5 stars
- **Use Case**: Quick visual indicator of candidate quality
- **Display**: Star icons in candidate lists

---

## 5. AI-Powered Features

### 5.1 CV Screening (Egis Standard)
- **Description**: Comprehensive CV analysis against JD requirements
- **Access**: Authenticated users
- **Endpoint**: `POST /api/ai/screen-candidate`
- **Inputs**:
  - candidate_id (with resume_url)
  - position_id (with requirements)
- **Process**:
  1. Create AIJob record (status=pending)
  2. Enqueue to background queue
  3. Download and extract CV text (PDF/DOCX)
  4. Call Gemini API with CV + JD
  5. Parse structured response
  6. Store in screening_runs table
  7. Update candidate.ai_score (JSON)
  8. Publish real-time event
- **Output Schema**:
  - candidate (name, email, phone)
  - table_1_screening_summary (overall_fit, recommended_roles, key_strengths, potential_gaps, notice_period)
  - table_2_compliance (requirement_category, requirement_description, compliance_status, evidence)
  - final_recommendation (summary, decision, justification)
  - record_management (screened_at_utc, screened_by, tags)
- **Decision Types**:
  - Proceed to technical interview
  - Suitable for a lower-grade role
  - Reject
- **Fallback**: Heuristic keyword matching
- **Activity Log**: ai_screening event

### 5.2 Document Analysis
- **Description**: Extract project/position info from uploaded files
- **Access**: Authenticated users
- **Endpoint**: `POST /api/ai/analyze-file`
- **Inputs**: document_id or file upload
- **Supported Formats**: PDF, DOCX, CSV, TXT
- **Process**:
  1. Extract text from document
  2. Classify document type (project_scope, job_description, positions_list, mixed, general)
  3. Parse project_info (name, client, sector, location, scope)
  4. Parse positions (title, department, experience, qualifications, requirements)
  5. Store in AIJob response_json
- **Use Case**: Upload RFP/SOW, extract project + positions automatically
- **Fallback**: Regex-based keyword extraction
- **Activity Log**: document_analysis event

### 5.3 Job Description Generation
- **Description**: AI-generated professional JDs
- **Access**: Authenticated users
- **Endpoint**: `POST /api/ai/generate-jd`
- **Inputs**: title, context (project_summary, sector, seniority)
- **Output**:
  - title, summary, description
  - responsibilities (bullet list)
  - requirements (core + nice-to-have)
  - compensation_note
- **Fallback**: Template-based with sensible defaults
- **Activity Log**: ai_jd_generated event

### 5.4 Market Research
- **Description**: Regional/sector talent market intelligence
- **Access**: Authenticated users
- **Endpoint**: `POST /api/research/market-analysis`
- **Inputs**: region, sector, optional project_id
- **Process**:
  1. Create ProjectMarketResearch record (status=pending)
  2. Enqueue background job
  3. Call Gemini API with region/sector context
  4. Parse findings and sources
  5. Store in database
  6. Link to project if provided
- **Output**:
  - region, sector, summary
  - findings (array of {title, description, leads})
  - sources (array of {title, url})
- **Caching**: Reuse recent research for same region+sector
- **Fallback**: Generic insights based on region/sector keywords
- **Activity Log**: ai_market_research event

### 5.5 Salary Benchmarking
- **Description**: Compensation data by role/region/seniority
- **Access**: Authenticated users
- **Endpoint**: `POST /api/research/salary-benchmark`
- **Inputs**: title, region, sector, seniority, currency
- **Process**:
  1. Check salary_benchmarks cache (90 days)
  2. If not cached, calculate via AI or fallback
  3. Store in database with sources
- **Output**:
  - currency, annual_min, annual_mid, annual_max
  - rationale (calculation explanation)
  - sources (Glassdoor, PayScale, Robert Half, Hays)
- **Fallback Calculation**:
  - Base role salary × seniority multiplier × regional adjustment × sector adjustment
  - Range: ±20% of midpoint
- **Activity Log**: salary_benchmark event

### 5.6 Candidate Scoring
- **Description**: Multi-dimensional fit assessment
- **Access**: Authenticated users
- **Process**: Called internally after CV screening
- **Inputs**: candidate skills, years_experience, leadership flag
- **Output**:
  - technical_fit (0-1.0)
  - cultural_alignment (0-1.0)
  - growth_potential (0-1.0)
  - match_score (weighted average)
  - notes (list of observations)
- **Storage**: candidate.ai_score JSON field
- **Fallback**: Heuristic scoring (skills count, experience bonus, leadership bonus)

### 5.7 Outreach Email Generation
- **Description**: Personalized candidate outreach emails
- **Access**: Authenticated users
- **Endpoint**: `POST /api/ai/generate-email`
- **Inputs**: candidate_name, title, company, template (standard/executive/technical), highlights
- **Output**:
  - subject (email subject line)
  - body (email content with personalization)
- **Templates**:
  - Standard: Conversational, 15-min call request
  - Executive: Formal, leadership focus
  - Technical: Technical pod, engineering focus
- **Storage**: outreach_runs table
- **Fallback**: Template substitution
- **Activity Log**: generate_email event

### 5.8 Call Script Generation
- **Description**: Structured recruiter call scripts
- **Access**: Authenticated users
- **Endpoint**: `POST /api/ai/call-script`
- **Inputs**: candidate_name, title, location, project context
- **Output**:
  - candidate, role, location
  - value_props (list)
  - sections (object):
    - introduction
    - context
    - motivation (questions list)
    - technical (questions list)
    - managerial (questions list)
    - commercial (questions list)
    - design (questions list)
    - objection_handling (array of {objection, response})
    - closing
- **Use Case**: Standardized screening calls
- **Fallback**: Default Egis-branded script
- **Activity Log**: call_script event

### 5.9 Chatbot Assistant
- **Description**: Conversational AI for recruitment tasks
- **Access**: Authenticated users
- **Endpoint**: `POST /api/chatbot`
- **Inputs**: message, session_id (optional)
- **Process**:
  1. Load or create chatbot_session
  2. Load conversation history (chatbot_messages)
  3. Call Gemini API with context
  4. Parse response
  5. Store message in database
  6. Return reply
- **Capabilities**:
  - Summarize pipeline status
  - Suggest sourcing strategies
  - Trigger market research
  - Provide salary benchmarks
- **Intent Detection**:
  - status, market_research, sourcing, salary, help
- **Fallback**: Intent-based canned responses
- **Activity Log**: chatbot_interaction event

### 5.10 Boolean Search Generation
- **Description**: LinkedIn X-Ray optimized search strings
- **Access**: Internal service
- **Function**: `build_boolean_search(persona)`
- **Inputs**: CandidatePersona (title, skills, location, seniority)
- **Output**: Google CSE compatible boolean string
- **Example**: `("Project Manager" OR ProjectManager) AND ("PMO" OR "Stakeholder Management") ("Dubai") ("Senior")`
- **Use Case**: Candidate sourcing automation

### 5.11 Verbal Screening Script Generation
- **Description**: Structured 20-30 minute screening call scripts
- **Access**: Authenticated users (future endpoint)
- **Inputs**: candidate_name, position, seniority, JD, CV summary
- **Output**: 8-section script:
  1. Introduction (3-4 mins)
  2. Core Experience (10-12 mins)
  3. Leadership & Stakeholders (4-6 mins)
  4. Seniority-Adaptive Questions (5-7 mins)
  5. Candidate Interpretation (4-5 mins)
  6. Motivation Pressure-Test (4-5 mins)
  7. Compensation & Logistics (3-4 mins)
  8. Closing (1-2 mins)
- **Adaptive Questions**: Adjust based on seniority (Junior IC, Senior IC, Manager, Director)
- **Use Case**: Standardized, evidence-based screening

---

## 6. Candidate Sourcing Features

### 6.1 LinkedIn X-Ray Search
- **Description**: Automated LinkedIn profile discovery via Google CSE
- **Access**: Authenticated users
- **Endpoint**: `POST /api/sourcing/linkedin-xray`
- **Inputs**:
  - persona (title, skills, location, seniority)
  - position_id (optional)
  - max_results (default 20)
- **Process**:
  1. Generate boolean search string
  2. Create SourcingJob record (status=pending)
  3. Enqueue background job
  4. Call Google Custom Search API
  5. Parse LinkedIn profile URLs
  6. Extract snippets
  7. Store in sourcing_results table
  8. Update job status=completed
- **Requirements**: RECRUITPRO_GOOGLE_API_KEY, RECRUITPRO_GOOGLE_CSE_ID
- **Fallback**: Return empty results with user notification
- **Activity Log**: ai_sourcing event

### 6.2 SmartRecruiters Bulk Import
- **Description**: Scrape candidates from SmartRecruiters platform
- **Access**: Authenticated users
- **Endpoint**: `POST /api/sourcing/smartrecruiters-bulk`
- **Inputs**:
  - company_id (SmartRecruiters company)
  - filters (position, status, tags)
  - credentials (email, password)
- **Process**:
  1. Create SourcingJob record
  2. Enqueue background job
  3. Launch Playwright browser
  4. Login to SmartRecruiters
  5. Navigate to candidate list
  6. Scrape candidate data (name, email, status, tags)
  7. Map to RecruitPro candidate schema
  8. Bulk import candidates
  9. Store source URLs in sourcing_results
- **Error Handling**:
  - SmartRecruitersLoginError: Auth failure
  - SmartRecruitersScrapeError: Data extraction failure
  - CAPTCHA detection: Manual intervention required
- **Activity Log**: smartrecruiters_import event

### 6.3 Sourcing Job Tracking
- **Description**: Monitor progress of sourcing jobs
- **Access**: Authenticated users
- **Endpoint**: `GET /api/sourcing/{job_id}/status`
- **Output**:
  - sourcing_job_id
  - status (pending, in_progress, completed, failed)
  - progress (0-100)
  - found_count
  - created_at, updated_at
  - error (if failed)
- **Polling**: Client polls every 5 seconds during sourcing

### 6.4 Sourcing Overview
- **Description**: All sourcing jobs and results
- **Access**: Authenticated users
- **Endpoint**: `GET /api/sourcing/overview`
- **Filters**: project_id (optional)
- **Output**:
  - Active sourcing jobs
  - Completed jobs
  - Result counts by platform
  - Quality score distribution

### 6.5 Sourcing Results Management
- **Description**: View and manage sourced profiles
- **Model**: sourcing_results table
- **Fields**:
  - result_id (PK)
  - sourcing_job_id (FK)
  - platform (LinkedIn, SmartRecruiters)
  - profile_url (unique per job)
  - name, title, company, location
  - summary (text)
  - quality_score (0-100)
- **Actions**:
  - Convert to candidate (create Candidate record)
  - Mark as contacted
  - Mark as not interested

### 6.6 Candidate Profile Synthesis (Testing)
- **Description**: Generate realistic test candidate profiles
- **Access**: Authenticated users
- **Function**: `synthesise_candidate_profiles(persona, count)`
- **Inputs**: CandidatePersona, count (number of profiles)
- **Output**: Array of candidate profiles with:
  - name, title, location, company
  - platform (LinkedIn)
  - profile_url (realistic format)
  - summary (professional bio)
  - quality_score (65-95)
- **Use Case**: Testing sourcing workflows, demo data

---

## 7. Interview Management Features

### 7.1 Schedule Interview
- **Description**: Create interview record
- **Access**: Authenticated users
- **Endpoint**: `POST /api/interviews`
- **Inputs**:
  - project_id, position_id, candidate_id
  - scheduled_at (datetime, future)
  - mode (phone, in-person, virtual)
  - location (optional)
  - notes (optional)
- **Validation**: scheduled_at must be future
- **Activity Log**: interview_scheduled event

### 7.2 List Interviews
- **Description**: View scheduled interviews
- **Access**: Authenticated users
- **Endpoint**: `GET /api/interviews`
- **Filters**:
  - project_id
  - position_id
  - candidate_id
  - date_range (from_date, to_date)
- **Sorting**: scheduled_at ASC (upcoming first)
- **Pagination**: page, limit

### 7.3 Update Interview
- **Description**: Modify interview details or add feedback
- **Access**: Interview creator or admin
- **Endpoint**: `PUT /api/interviews/{id}`
- **Updatable Fields**:
  - scheduled_at
  - mode
  - location
  - notes (append or replace)
  - feedback (text - post-interview)
- **Audit**: updated_by, updated_at tracked
- **Activity Log**: interview_updated event

### 7.4 Cancel Interview
- **Description**: Delete interview record
- **Access**: Interview creator or admin
- **Endpoint**: `DELETE /api/interviews/{id}`
- **Activity Log**: interview_cancelled event

### 7.5 Upcoming Interviews Widget
- **Description**: Dashboard display of next 5 interviews
- **Location**: Main dashboard (`/app`)
- **Display**:
  - Candidate name (linked to profile)
  - Position title
  - Scheduled date/time
  - Mode badge (phone/in-person/virtual)
  - Quick actions (view, update, cancel)

---

## 8. Document Management Features

### 8.1 Upload Document
- **Description**: Upload files to system
- **Access**: Authenticated users
- **Endpoint**: `POST /api/documents/upload`
- **Inputs**:
  - file (multipart/form-data)
  - scope (project, candidate, user)
  - scope_id (project_id, candidate_id, user_id)
- **Supported Formats**: PDF, DOCX, CSV, TXT
- **File Size Limit**: 50 MB
- **Validation**:
  - MIME type whitelist
  - File size check
  - Filename sanitization
  - Virus scanning (ClamAV - future)
- **Storage**: `/storage/{scope}/{scope_id}/{filename}`
- **Database**: documents table (id, filename, file_url, mime_type, owner_user, scope, scope_id, uploaded_at)
- **Activity Log**: document_uploaded event

### 8.2 List Documents
- **Description**: View uploaded documents
- **Access**: Authenticated users
- **Endpoint**: `GET /api/documents`
- **Filters**:
  - scope (project, candidate, user)
  - scope_id
  - mime_type
- **Output**: Paginated document list with metadata

### 8.3 Download Document
- **Description**: Retrieve uploaded file
- **Access**: Authenticated users with access to scope
- **Endpoints**:
  - `GET /api/documents/{id}`
  - `GET /api/documents/{id}/download`
  - `GET /storage/{scope}/{scope_id}/{filename}` (direct)
- **Authorization**: User must have access to document's scope (project owner, candidate owner, admin)
- **Response**: File stream with appropriate Content-Type header

### 8.4 Delete Document
- **Description**: Remove file from system
- **Access**: Document owner or admin
- **Endpoint**: `DELETE /api/documents/{id}`
- **Process**:
  1. Verify permissions
  2. Delete file from storage
  3. Delete database record
- **Activity Log**: document_deleted event

---

## 9. Activity & Reporting Features

### 9.1 Activity Feed
- **Description**: Audit trail of all user and system actions
- **Access**: Authenticated users
- **Endpoint**: `GET /api/activity`
- **Filters**:
  - actor_type (user, system, ai)
  - actor_id
  - event_type
  - project_id, position_id, candidate_id
  - date_range (from_date, to_date)
- **Pagination**: page, limit
- **Sorting**: created_at DESC
- **Event Types Logged**:
  - Authentication: login, logout, user_registered, password_changed
  - Projects: project_created, project_updated, project_archived
  - Positions: position_created, position_updated, position_deleted
  - Candidates: candidate_added, candidate_updated, candidate_status_changed, candidate_deleted
  - Interviews: interview_scheduled, interview_updated
  - AI: ai_screening, ai_jd_generated, ai_sourcing, ai_market_research
  - Documents: document_uploaded, document_deleted

### 9.2 Real-Time Activity Stream
- **Description**: Server-Sent Events (SSE) for live updates
- **Access**: Authenticated users
- **Endpoint**: `GET /api/activity/stream`
- **Protocol**: SSE (text/event-stream)
- **Events**: JSON payloads pushed to connected clients
- **Keep-Alive**: Heartbeat every 30 seconds
- **Use Case**: Dashboard live activity feed

### 9.3 Dashboard Statistics
- **Description**: Summary metrics for dashboard
- **Access**: Authenticated users
- **Endpoint**: `GET /api/activity/dashboard/stats`
- **Output**:
  - project_count (total, by status)
  - position_count (total, by status)
  - candidate_count (total, by status)
  - sourcing_job_count (active)
  - recent_activity_count (last 7 days)
  - upcoming_interviews_count
- **Caching**: Consider Redis cache for performance

---

## 10. Admin & Configuration Features

### 10.1 Integration Configuration
- **Description**: Configure external service credentials
- **Access**: Admin, super_admin
- **Endpoint**:
  - `GET /api/settings` (view integration status)
  - `POST /api/settings` (update credentials)
- **Integrations**:
  - **Gemini API**: api_key
  - **Google Custom Search**: api_key, cse_id
  - **SmartRecruiters**: email, password
- **Storage**: integration_credentials table (encrypted)
- **Encryption**: AES-256-GCM via app/utils/secrets.py
- **Display**: API keys masked (show last 4 chars)
- **Activity Log**: integration_updated event

### 10.2 System Health Check
- **Description**: Comprehensive health monitoring
- **Access**: Public (no auth required)
- **Endpoint**: `GET /api/health`
- **Checks**:
  - Database connectivity (SELECT 1)
  - Background queue status (in-memory or Redis)
  - Redis/RQ status (if configured)
  - Gemini API configuration (key present)
- **Response**:
  - status (healthy, degraded, unhealthy)
  - components (object with individual checks)
  - timestamp
- **Use Case**: Load balancer health checks, monitoring alerts

---

## Feature Matrix by Role

| Feature Category | Recruiter | Admin | Super Admin |
|------------------|-----------|-------|-------------|
| **User Management** | Own profile | All users, role changes | Full user CRUD |
| **Projects** | Own projects | All projects | All projects |
| **Positions** | Own projects | All positions | All positions |
| **Candidates** | Own candidates | All candidates | All candidates |
| **AI Features** | ✓ All | ✓ All | ✓ All |
| **Sourcing** | ✓ All | ✓ All | ✓ All |
| **Interviews** | Own interviews | All interviews | All interviews |
| **Documents** | Own scope | All documents | All documents |
| **Activity Feed** | Own activity | All activity | All activity |
| **Admin Settings** | ✗ | ✓ Integrations | ✓ All settings |
| **System Health** | ✓ View | ✓ View | ✓ View |

---

## Feature Toggles & Flags

**Location**: `advanced_features_config` table

**Available Flags**:
```json
{
  "chatbot.tool_suggestions": {
    "market_research": true,
    "salary_benchmark": true,
    "bulk_outreach": true
  },
  "sourcing.smartrecruiters_enabled": true,
  "screening.require_ai_score": true,
  "documents.auto_analyze_on_upload": true,
  "research.auto_run_market_research": true
}
```

**Management**:
- `GET /api/admin/advanced/features` - List all flags
- `PUT /api/admin/advanced/features/{key}` - Update flag value

---

## Future Features (Roadmap)

### Phase 2 (Planned)
- Video interviewing integration (Zoom, Teams)
- Email/calendar integration (Gmail, Outlook)
- Candidate portal (self-service application, status tracking)
- Advanced analytics (time-to-hire, source effectiveness, conversion rates)
- Mobile app (iOS, Android)

### Phase 3 (Planned)
- Background checks integration
- Offer letter generation
- Onboarding workflows
- Multi-language support
- LDAP/SSO authentication
- Vector search for semantic candidate matching

---

**End of System Features Documentation**
