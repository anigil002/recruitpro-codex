# RecruitPro - Requirements Traceability Matrix

**Version:** 1.0
**Date:** November 25, 2025
**Purpose:** Map requirements to implementation components, ensuring complete coverage

---

## Table of Contents

1. [Overview](#overview)
2. [Business Requirements Traceability](#business-requirements-traceability)
3. [Functional Requirements Traceability](#functional-requirements-traceability)
4. [Non-Functional Requirements Traceability](#non-functional-requirements-traceability)
5. [Database Schema Mapping](#database-schema-mapping)
6. [API Endpoint Mapping](#api-endpoint-mapping)
7. [Test Coverage Matrix](#test-coverage-matrix)

---

## Overview

This traceability matrix ensures every requirement is implemented, tested, and documented. It provides bidirectional traceability from requirements to code and from code back to requirements.

### Legend

- **✓** Implemented
- **△** Partially Implemented
- **✗** Not Implemented
- **N/A** Not Applicable

---

## Business Requirements Traceability

| Req ID | Requirement | Status | Implementation Files | API Endpoints | Database Tables | Tests |
|--------|-------------|--------|----------------------|---------------|-----------------|-------|
| **BR-001** | Multi-Project Management | ✓ | `app/models/project.py`<br>`app/routers/projects.py`<br>`app/services/project.py` | `POST /api/projects`<br>`GET /api/projects`<br>`GET /api/projects/{id}`<br>`PUT /api/projects/{id}`<br>`DELETE /api/projects/{id}` | `projects` | `tests/test_projects.py` |
| **BR-002** | Position Tracking | ✓ | `app/models/position.py`<br>`app/routers/positions.py`<br>`app/services/position.py` | `POST /api/projects/{id}/positions`<br>`GET /api/positions`<br>`GET /api/positions/{id}`<br>`PUT /api/positions/{id}`<br>`DELETE /api/positions/{id}` | `positions` | `tests/test_projects.py` |
| **BR-003** | Candidate Pipeline | ✓ | `app/models/candidate.py`<br>`app/models/candidate_status_history.py`<br>`app/routers/candidates.py`<br>`app/services/candidate.py` | `POST /api/candidates`<br>`GET /api/candidates`<br>`GET /api/candidates/{id}`<br>`PUT /api/candidates/{id}`<br>`PATCH /api/candidates/{id}` | `candidates`<br>`candidate_status_history` | `tests/test_candidates.py` |
| **BR-004** | AI CV Screening | ✓ | `app/services/gemini.py::screen_cv()`<br>`app/services/ai.py`<br>`app/routers/ai.py` | `POST /api/ai/screen-candidate` | `ai_jobs`<br>`screening_runs`<br>`candidates.ai_score` | `tests/test_ai_integrations.py`<br>`tests/test_gemini_parsing.py` |
| **BR-005** | Market Intelligence | ✓ | `app/services/gemini.py::generate_market_research()`<br>`app/services/gemini.py::generate_salary_benchmark()`<br>`app/routers/research.py` | `POST /api/research/market-analysis`<br>`POST /api/research/salary-benchmark` | `project_market_research`<br>`salary_benchmarks` | `tests/test_ai_integrations.py` |
| **BR-006** | Sourcing Automation | ✓ | `app/services/sourcing.py`<br>`app/services/smartrecruiters.py`<br>`app/routers/sourcing.py` | `POST /api/sourcing/linkedin-xray`<br>`POST /api/sourcing/smartrecruiters-bulk`<br>`GET /api/sourcing/overview` | `sourcing_jobs`<br>`sourcing_results` | `tests/test_smartrecruiters_integration.py` |
| **BR-007** | Document Management | ✓ | `app/models/document.py`<br>`app/models/project_document.py`<br>`app/routers/documents.py`<br>`app/services/storage.py` | `POST /api/documents/upload`<br>`GET /api/documents`<br>`GET /api/documents/{id}`<br>`DELETE /api/documents/{id}` | `documents`<br>`project_documents` | `tests/test_ai_integrations.py` |
| **BR-008** | Interview Scheduling | ✓ | `app/models/interview.py`<br>`app/routers/interviews.py`<br>`app/services/interview.py` | `POST /api/interviews`<br>`GET /api/interviews`<br>`PUT /api/interviews/{id}`<br>`DELETE /api/interviews/{id}` | `interviews` | `tests/test_interviews.py` |
| **BR-009** | Activity Auditing | ✓ | `app/models/activity_feed.py`<br>`app/routers/activity.py`<br>`app/services/events.py` | `GET /api/activity`<br>`GET /api/activity/stream`<br>`GET /api/activity/dashboard/stats` | `activity_feed` | `tests/test_activity_security.py` |
| **BR-010** | User Access Management | ✓ | `app/models/user.py`<br>`app/routers/auth.py`<br>`app/routers/admin.py`<br>`app/utils/security.py` | `POST /api/auth/register`<br>`POST /api/auth/login`<br>`POST /api/auth/logout`<br>`GET /api/admin/users` | `users` | `tests/test_auth.py` |

---

## Functional Requirements Traceability

### Authentication & Authorization

| Req ID | Requirement | Implementation | Endpoints | Models | Services | Tests | Status |
|--------|-------------|----------------|-----------|--------|----------|-------|--------|
| **FR-AUTH-001** | User Registration | `app/routers/auth.py:26-64` | `POST /api/auth/register` | `User` | `create_user()` | `test_auth.py::test_register_user` | ✓ |
| **FR-AUTH-002** | User Login | `app/routers/auth.py:66-104` | `POST /api/auth/login` | `User` | `authenticate_user()` | `test_auth.py::test_login_success` | ✓ |
| **FR-AUTH-003** | JWT Token Session | `app/utils/security.py:150-180`<br>`app/deps.py:30-65` | All protected endpoints | - | `create_access_token()`<br>`get_current_user()` | `test_auth.py::test_token_validation` | ✓ |
| **FR-AUTH-004** | Password Change | `app/routers/auth.py:106-140` | `POST /api/auth/change-password` | `User`<br>`PasswordHistory` | `verify_password()`<br>`hash_password()` | `test_auth.py::test_change_password` | ✓ |
| **FR-AUTH-005** | RBAC | `app/utils/security.py:200-220`<br>`app/deps.py:67-90` | Admin endpoints | `User.role` | `can_manage_workspace()`<br>`require_admin()` | `test_auth.py::test_role_based_access` | ✓ |

### Project Management

| Req ID | Requirement | Implementation | Endpoints | Models | Services | Tests | Status |
|--------|-------------|----------------|-----------|--------|----------|-------|--------|
| **FR-PROJ-001** | Create Project | `app/routers/projects.py:40-85` | `POST /api/projects` | `Project` | `create_project()` | `test_projects.py::test_create_project` | ✓ |
| **FR-PROJ-002** | List Projects | `app/routers/projects.py:87-130` | `GET /api/projects` | `Project` | `list_projects()` | `test_projects.py::test_list_projects` | ✓ |
| **FR-PROJ-003** | View Project Details | `app/routers/projects.py:132-180` | `GET /api/projects/{id}` | `Project`<br>`Position`<br>`Candidate` | `get_project_details()` | `test_projects.py::test_get_project` | ✓ |
| **FR-PROJ-004** | Update Project | `app/routers/projects.py:182-230` | `PUT /api/projects/{id}` | `Project` | `update_project()` | `test_projects.py::test_update_project` | ✓ |
| **FR-PROJ-005** | Archive/Delete Project | `app/routers/projects.py:232-270` | `DELETE /api/projects/{id}` | `Project` | `delete_project()` | `test_projects.py::test_delete_project` | ✓ |
| **FR-PROJ-006** | Bulk Status Update | `app/routers/projects.py:272-310` | `PATCH /api/projects/bulk/lifecycle` | `Project` | `bulk_update_status()` | - | ✓ |

### Position Management

| Req ID | Requirement | Implementation | Endpoints | Models | Services | Tests | Status |
|--------|-------------|----------------|-----------|--------|----------|-------|--------|
| **FR-POS-001** | Create Position | `app/routers/positions.py:35-90` | `POST /api/projects/{id}/positions` | `Position` | `create_position()` | `test_projects.py::test_create_position` | ✓ |
| **FR-POS-002** | List Positions | `app/routers/positions.py:92-140` | `GET /api/positions` | `Position` | `list_positions()` | `test_projects.py::test_list_positions` | ✓ |
| **FR-POS-003** | View Position Details | `app/routers/positions.py:142-180` | `GET /api/positions/{id}` | `Position`<br>`Candidate` | `get_position_details()` | `test_projects.py::test_get_position` | ✓ |
| **FR-POS-004** | Update Position | `app/routers/positions.py:182-230` | `PUT /api/positions/{id}` | `Position` | `update_position()` | `test_projects.py::test_update_position` | ✓ |
| **FR-POS-005** | Delete Position | `app/routers/positions.py:232-260` | `DELETE /api/positions/{id}` | `Position` | `delete_position()` | `test_projects.py::test_delete_position` | ✓ |

### Candidate Management

| Req ID | Requirement | Implementation | Endpoints | Models | Services | Tests | Status |
|--------|-------------|----------------|-----------|--------|----------|-------|--------|
| **FR-CAND-001** | Create Candidate | `app/routers/candidates.py:50-110` | `POST /api/candidates` | `Candidate` | `create_candidate()` | `test_candidates.py::test_create_candidate` | ✓ |
| **FR-CAND-002** | List Candidates | `app/routers/candidates.py:112-180` | `GET /api/candidates` | `Candidate` | `list_candidates()` | `test_candidates.py::test_list_candidates` | ✓ |
| **FR-CAND-003** | View Profile | `app/routers/candidates.py:182-240` | `GET /api/candidates/{id}` | `Candidate`<br>`ScreeningRun`<br>`StatusHistory` | `get_candidate_details()` | `test_candidates.py::test_get_candidate` | ✓ |
| **FR-CAND-004** | Update Candidate | `app/routers/candidates.py:242-310` | `PUT /api/candidates/{id}`<br>`PATCH /api/candidates/{id}` | `Candidate`<br>`StatusHistory` | `update_candidate()`<br>`track_status_change()` | `test_candidates.py::test_update_candidate` | ✓ |
| **FR-CAND-005** | Soft Delete | `app/routers/candidates.py:312-350` | `DELETE /api/candidates/{id}` | `Candidate` | `soft_delete_candidate()` | `test_candidates.py::test_delete_candidate` | ✓ |
| **FR-CAND-006** | Bulk Operations | `app/routers/candidates.py:352-420` | `POST /api/candidates/bulk`<br>`POST /api/candidates/bulk-action` | `Candidate` | `bulk_create()`<br>`bulk_update_status()` | `test_candidates.py::test_bulk_operations` | ✓ |
| **FR-CAND-007** | Import | `app/routers/candidates.py:422-500` | `POST /api/candidates/import` | `Candidate` | `import_from_csv()` | - | ✓ |
| **FR-CAND-008** | Export | `app/routers/candidates.py:502-560` | `GET /api/candidates/export` | `Candidate` | `export_to_csv()` | - | ✓ |

### AI Features

| Req ID | Requirement | Implementation | Endpoints | Models | Services | Tests | Status |
|--------|-------------|----------------|-----------|--------|----------|-------|--------|
| **FR-AI-001** | CV Screening | `app/services/gemini.py:450-750`<br>`app/routers/ai.py:40-120` | `POST /api/ai/screen-candidate` | `AIJob`<br>`ScreeningRun`<br>`Candidate.ai_score` | `screen_cv()`<br>`_handle_cv_screening_job()` | `test_ai_integrations.py::test_cv_screening`<br>`test_gemini_parsing.py` | ✓ |
| **FR-AI-002** | Document Analysis | `app/services/gemini.py:752-950`<br>`app/routers/ai.py:122-180` | `POST /api/ai/analyze-file` | `AIJob` | `analyze_file()`<br>`_handle_file_analysis_job()` | `test_ai_integrations.py::test_analyze_file` | ✓ |
| **FR-AI-003** | JD Generation | `app/services/gemini.py:250-400`<br>`app/routers/ai.py:182-230` | `POST /api/ai/generate-jd` | `AIJob` | `generate_job_description()` | `test_ai_integrations.py::test_jd_generation` | ✓ |
| **FR-AI-004** | Market Research | `app/services/gemini.py:952-1150`<br>`app/routers/research.py:30-100` | `POST /api/research/market-analysis` | `ProjectMarketResearch`<br>`AIJob` | `generate_market_research()`<br>`_handle_market_research_job()` | `test_ai_integrations.py::test_market_research` | ✓ |
| **FR-AI-005** | Salary Benchmark | `app/services/gemini.py:1152-1350`<br>`app/routers/research.py:102-160` | `POST /api/research/salary-benchmark` | `SalaryBenchmark` | `generate_salary_benchmark()` | `test_ai_integrations.py::test_salary_benchmark` | ✓ |
| **FR-AI-006** | Candidate Scoring | `app/services/gemini.py:402-548` | - | `Candidate.ai_score` | `score_candidate()` | `test_ai_integrations.py::test_candidate_scoring` | ✓ |
| **FR-AI-007** | Email Generation | `app/services/gemini.py:1352-1500`<br>`app/routers/ai.py:232-280` | `POST /api/ai/generate-email` | `OutreachRun` | `generate_outreach_email()` | - | ✓ |
| **FR-AI-008** | Call Script | `app/services/gemini.py:1502-1700`<br>`app/routers/ai.py:282-330` | `POST /api/ai/call-script` | `OutreachRun` | `generate_call_script()` | - | ✓ |
| **FR-AI-009** | Chatbot | `app/services/gemini.py:1702-1950`<br>`app/routers/ai.py:332-400` | `POST /api/chatbot` | `ChatbotSession`<br>`ChatbotMessage` | `generate_chatbot_reply()` | `test_chatbot.py` | ✓ |
| **FR-AI-010** | Boolean Search | `app/services/gemini.py:1952-2100` | - | - | `build_boolean_search()` | - | ✓ |

### Candidate Sourcing

| Req ID | Requirement | Implementation | Endpoints | Models | Services | Tests | Status |
|--------|-------------|----------------|-----------|--------|----------|-------|--------|
| **FR-SRC-001** | LinkedIn X-Ray | `app/services/sourcing.py:50-250`<br>`app/routers/sourcing.py:40-110` | `POST /api/sourcing/linkedin-xray` | `SourcingJob`<br>`SourcingResult` | `linkedin_xray_search()`<br>`_handle_sourcing_linkedin_job()` | - | ✓ |
| **FR-SRC-002** | SmartRecruiters | `app/services/smartrecruiters.py`<br>`app/routers/sourcing.py:112-180` | `POST /api/sourcing/smartrecruiters-bulk` | `SourcingJob`<br>`SourcingResult`<br>`Candidate` | `scrape_candidates()`<br>`_handle_sourcing_smartrecruiters_job()` | `test_smartrecruiters_integration.py` | ✓ |
| **FR-SRC-003** | Job Tracking | `app/routers/sourcing.py:182-220` | `GET /api/sourcing/{job_id}/status` | `SourcingJob` | `get_sourcing_job_status()` | - | ✓ |
| **FR-SRC-004** | Sourcing Overview | `app/routers/sourcing.py:30-38` | `GET /api/sourcing/overview` | `SourcingJob`<br>`SourcingResult` | `get_sourcing_overview()` | - | ✓ |

### Document Management

| Req ID | Requirement | Implementation | Endpoints | Models | Services | Tests | Status |
|--------|-------------|----------------|-----------|--------|----------|-------|--------|
| **FR-DOC-001** | Upload | `app/routers/documents.py:35-110`<br>`app/services/storage.py:20-80` | `POST /api/documents/upload` | `Document`<br>`ProjectDocument` | `save_file()`<br>`create_document()` | - | ✓ |
| **FR-DOC-002** | List | `app/routers/documents.py:112-160` | `GET /api/documents` | `Document` | `list_documents()` | - | ✓ |
| **FR-DOC-003** | Download | `app/routers/documents.py:162-210`<br>`app/main.py:80-95` | `GET /api/documents/{id}`<br>`GET /storage/{path}` | `Document` | `get_file_path()` | - | ✓ |
| **FR-DOC-004** | Delete | `app/routers/documents.py:212-250` | `DELETE /api/documents/{id}` | `Document` | `delete_file()`<br>`delete_document()` | - | ✓ |

### Interview Management

| Req ID | Requirement | Implementation | Endpoints | Models | Services | Tests | Status |
|--------|-------------|----------------|-----------|--------|----------|-------|--------|
| **FR-INT-001** | Schedule | `app/routers/interviews.py:35-90` | `POST /api/interviews` | `Interview` | `create_interview()` | `test_interviews.py::test_create_interview` | ✓ |
| **FR-INT-002** | List | `app/routers/interviews.py:92-140` | `GET /api/interviews` | `Interview` | `list_interviews()` | `test_interviews.py::test_list_interviews` | ✓ |
| **FR-INT-003** | Update | `app/routers/interviews.py:142-200` | `PUT /api/interviews/{id}` | `Interview` | `update_interview()` | `test_interviews.py::test_update_interview` | ✓ |
| **FR-INT-004** | Cancel | `app/routers/interviews.py:202-230` | `DELETE /api/interviews/{id}` | `Interview` | `delete_interview()` | `test_interviews.py::test_delete_interview` | ✓ |

### Activity & Reporting

| Req ID | Requirement | Implementation | Endpoints | Models | Services | Tests | Status |
|--------|-------------|----------------|-----------|--------|----------|-------|--------|
| **FR-ACT-001** | Activity Logging | `app/services/events.py:20-150`<br>`app/models/activity_feed.py` | All endpoints | `ActivityFeed` | `log_activity()`<br>`publish_sync()` | `test_activity_security.py` | ✓ |
| **FR-ACT-002** | Activity Feed | `app/routers/activity.py:35-90` | `GET /api/activity` | `ActivityFeed` | `get_activity_feed()` | `test_activity_security.py::test_activity_feed` | ✓ |
| **FR-ACT-003** | Real-Time Stream | `app/routers/activity.py:92-140` | `GET /api/activity/stream` | `ActivityFeed` | `stream_activity()` | - | ✓ |
| **FR-REP-001** | Dashboard Stats | `app/routers/activity.py:142-220` | `GET /api/activity/dashboard/stats` | Multiple | `get_dashboard_stats()` | - | ✓ |
| **FR-REP-002** | Analytics | `app/routers/reporting.py:30-150` | `GET /api/reporting/overview` | Multiple | `get_analytics_overview()` | - | ✓ |

### Administration

| Req ID | Requirement | Implementation | Endpoints | Models | Services | Tests | Status |
|--------|-------------|----------------|-----------|--------|----------|-------|--------|
| **FR-ADM-001** | User Management | `app/routers/admin.py:40-120` | `GET /api/admin/users`<br>`POST /api/admin/users/{id}/role` | `User` | `list_users()`<br>`change_user_role()` | `test_auth.py::test_admin_endpoints` | ✓ |
| **FR-ADM-002** | Integration Config | `app/routers/settings.py:30-140`<br>`app/utils/secrets.py` | `GET /api/settings`<br>`POST /api/settings` | `IntegrationCredential` | `get_integration_status()`<br>`update_credentials()` | - | ✓ |
| **FR-ADM-003** | Feature Flags | `app/routers/admin.py:180-250` | `GET /api/admin/advanced/features`<br>`PUT /api/admin/advanced/features/{key}` | `AdvancedFeaturesConfig` | `get_features()`<br>`update_feature()` | - | ✓ |
| **FR-ADM-004** | Bulk Migration | `app/routers/admin.py:252-350` | `POST /api/admin/migrate-from-json` | Multiple | `migrate_from_json()` | - | ✓ |
| **FR-ADM-005** | Health Check | `app/routers/system.py:30-120` | `GET /api/health` | - | `check_health()` | `test_health.py` | ✓ |
| **FR-ADM-006** | Version Info | `app/routers/system.py:122-150` | `GET /api/version` | - | `get_version()` | `test_health.py::test_version` | ✓ |

---

## Non-Functional Requirements Traceability

| Category | Req ID | Requirement | Implementation | Verification Method | Status |
|----------|--------|-------------|----------------|---------------------|--------|
| **Performance** | NFR-PERF-001 | Response Time < 2s | FastAPI async handlers<br>Database indexing<br>Query optimization | Load testing<br>Prometheus metrics | ✓ |
| **Performance** | NFR-PERF-002 | 100 Concurrent Users | Uvicorn ASGI server<br>Connection pooling<br>Async I/O | Load testing (Locust/JMeter) | △ |
| **Performance** | NFR-PERF-003 | DB Query < 500ms | SQLAlchemy indexes<br>Query optimization<br>Pagination | Query logging<br>Slow query alerts | ✓ |
| **Performance** | NFR-PERF-004 | File Upload Speed | Streaming uploads<br>Chunked processing | Upload benchmarks | ✓ |
| **Performance** | NFR-PERF-005 | AI Latency < 30s | Timeout configuration<br>Fallback logic | Integration tests | ✓ |
| **Scalability** | NFR-SCAL-001 | 1M+ Records | PostgreSQL<br>Proper indexing<br>Pagination | Database testing | ✓ |
| **Scalability** | NFR-SCAL-002 | Horizontal Scaling | Stateless JWT<br>Centralized storage<br>No server sessions | Multi-instance deployment | ✓ |
| **Scalability** | NFR-SCAL-003 | 1000+ Background Jobs | Redis + RQ<br>Multiple workers<br>Priority queues | Queue load testing | ✓ |
| **Reliability** | NFR-REL-001 | 99.5% Uptime | Health checks<br>Error handling<br>Monitoring | Uptime monitoring | △ |
| **Reliability** | NFR-REL-002 | Zero Data Loss | PostgreSQL WAL<br>Daily backups<br>PITR | Backup testing | △ |
| **Reliability** | NFR-REL-003 | Graceful Degradation | AI fallback logic<br>Error handling | `app/services/gemini.py` fallbacks | ✓ |
| **Reliability** | NFR-REL-004 | Job Retry | Exponential backoff<br>Tenacity library<br>Error logging | `app/services/gemini.py:50-80` | ✓ |
| **Usability** | NFR-USE-001 | Responsive UI | Tailwind CSS<br>Mobile-first design | Browser testing (multiple sizes) | ✓ |
| **Usability** | NFR-USE-002 | WCAG 2.1 AA | ARIA labels<br>Keyboard navigation<br>Color contrast | Accessibility audit (Lighthouse) | △ |
| **Usability** | NFR-USE-003 | Browser Support | Modern browser compatibility<br>Polyfills | Cross-browser testing | ✓ |
| **Usability** | NFR-USE-004 | Clear Errors | User-friendly messages<br>Error codes<br>Suggestions | `app/utils/exceptions.py` | ✓ |
| **Maintainability** | NFR-MAIN-001 | Code Quality | Ruff linting<br>Black formatting<br>Type hints | CI/CD pipeline | ✓ |
| **Maintainability** | NFR-MAIN-002 | 70% Test Coverage | pytest suite<br>Integration tests | Coverage reports | △ |
| **Maintainability** | NFR-MAIN-003 | API Documentation | FastAPI auto-docs<br>OpenAPI schema | `/docs`, `/redoc` | ✓ |
| **Maintainability** | NFR-MAIN-004 | Logging | Structured logging<br>JSON format<br>30-day retention | Log aggregation | ✓ |

---

## Database Schema Mapping

### Entity-Relationship Diagram

```
┌──────────────┐       ┌──────────────┐       ┌──────────────────┐
│    users     │       │   projects   │       │    positions     │
├──────────────┤       ├──────────────┤       ├──────────────────┤
│ user_id (PK) │◄──────┤ created_by   │       │ position_id (PK) │
│ email        │       │ project_id   │◄──────┤ project_id (FK)  │
│ password_hash│       │ name         │       │ title            │
│ role         │       │ client       │       │ requirements     │
└──────────────┘       └──────────────┘       └──────────────────┘
       │                      │                        │
       │                      │                        │
       │                      ▼                        ▼
       │               ┌──────────────┐       ┌──────────────────┐
       │               │  candidates  │       │ screening_runs   │
       │               ├──────────────┤       ├──────────────────┤
       └───────────────┤ created_by   │       │ screening_id (PK)│
                       │ candidate_id │◄──────┤ candidate_id (FK)│
                       │ project_id   │       │ position_id (FK) │
                       │ ai_score     │       │ overall_fit      │
                       └──────────────┘       └──────────────────┘
                              │
                              ▼
                       ┌──────────────────────┐
                       │candidate_status_hist │
                       ├──────────────────────┤
                       │ history_id (PK)      │
                       │ candidate_id (FK)    │
                       │ old_status           │
                       │ new_status           │
                       └──────────────────────┘
```

### Table-to-Requirement Mapping

| Table Name | Primary Key | Related Requirements | File | Indexes |
|------------|-------------|----------------------|------|---------|
| `users` | user_id | FR-AUTH-001 to FR-AUTH-005, FR-ADM-001 | `app/models/user.py` | email (UNIQUE) |
| `password_history` | history_id | FR-AUTH-004, SR-001 | `app/models/password_history.py` | user_id, created_at |
| `projects` | project_id | BR-001, FR-PROJ-001 to FR-PROJ-006 | `app/models/project.py` | created_by, status, created_at |
| `positions` | position_id | BR-002, FR-POS-001 to FR-POS-005 | `app/models/position.py` | project_id, status, created_at<br>UNIQUE(project_id, title, location) |
| `candidates` | candidate_id | BR-003, FR-CAND-001 to FR-CAND-008 | `app/models/candidate.py` | project_id, position_id, status, email, created_by, created_at |
| `candidate_status_history` | history_id | FR-CAND-004 | `app/models/candidate_status_history.py` | candidate_id, changed_at |
| `ai_jobs` | job_id | BR-004, FR-AI-001 to FR-AI-009 | `app/models/ai_job.py` | job_type, status, project_id, candidate_id, created_at |
| `screening_runs` | screening_id | BR-004, FR-AI-001 | `app/models/screening_run.py` | candidate_id, position_id, created_at |
| `sourcing_jobs` | sourcing_job_id | BR-006, FR-SRC-001 to FR-SRC-004 | `app/models/sourcing_job.py` | project_id, position_id, status, created_at |
| `sourcing_results` | result_id | BR-006, FR-SRC-001, FR-SRC-002 | `app/models/sourcing_result.py` | sourcing_job_id, platform<br>UNIQUE(sourcing_job_id, profile_url) |
| `project_market_research` | research_id | BR-005, FR-AI-004 | `app/models/project_market_research.py` | project_id, status, created_at |
| `salary_benchmarks` | benchmark_id | BR-005, FR-AI-005 | `app/models/salary_benchmark.py` | title, region, sector, seniority, created_at |
| `documents` | id | BR-007, FR-DOC-001 to FR-DOC-004 | `app/models/document.py` | owner_user, scope, uploaded_at |
| `project_documents` | doc_id | BR-007, FR-DOC-001 to FR-DOC-004 | `app/models/project_document.py` | project_id, uploaded_at |
| `interviews` | interview_id | BR-008, FR-INT-001 to FR-INT-004 | `app/models/interview.py` | project_id, position_id, candidate_id, scheduled_at |
| `activity_feed` | activity_id | BR-009, FR-ACT-001 to FR-ACT-003 | `app/models/activity_feed.py` | actor_type, actor_id, event_type, project_id, created_at |
| `chatbot_sessions` | session_id | FR-AI-009 | `app/models/chatbot_session.py` | user_id, created_at |
| `chatbot_messages` | message_id | FR-AI-009 | `app/models/chatbot_message.py` | session_id, created_at |
| `communication_templates` | template_id | FR-AI-007, FR-AI-008 | `app/models/communication_template.py` | type, created_by |
| `outreach_runs` | outreach_id | FR-AI-007, FR-AI-008 | `app/models/outreach_run.py` | user_id, candidate_id, created_at |
| `advanced_features_config` | key (PK) | FR-ADM-003 | `app/models/advanced_features_config.py` | - |
| `integration_credentials` | key (PK) | FR-ADM-002, IR-001 to IR-003 | `app/models/integration_credential.py` | - |
| `embeddings_index_refs` | index_id | Future feature | `app/models/embeddings_index_ref.py` | created_by |
| `admin_migration_logs` | log_id | FR-ADM-004 | `app/models/admin_migration_log.py` | created_at |

---

## API Endpoint Mapping

### Complete API Endpoint Inventory

| Endpoint | Method | Router File | Handler Function | Requirements | Auth | Tests |
|----------|--------|-------------|------------------|--------------|------|-------|
| `/api/auth/register` | POST | `routers/auth.py` | `register()` | FR-AUTH-001 | None | `test_auth.py::test_register_user` |
| `/api/auth/login` | POST | `routers/auth.py` | `login()` | FR-AUTH-002 | None | `test_auth.py::test_login_success` |
| `/api/auth/logout` | POST | `routers/auth.py` | `logout()` | FR-ACT-001 | Required | `test_auth.py::test_logout` |
| `/api/auth/change-password` | POST | `routers/auth.py` | `change_password()` | FR-AUTH-004 | Required | `test_auth.py::test_change_password` |
| `/api/projects` | GET | `routers/projects.py` | `list_projects()` | FR-PROJ-002 | Required | `test_projects.py::test_list_projects` |
| `/api/projects` | POST | `routers/projects.py` | `create_project()` | FR-PROJ-001 | Required | `test_projects.py::test_create_project` |
| `/api/projects/{id}` | GET | `routers/projects.py` | `get_project()` | FR-PROJ-003 | Required | `test_projects.py::test_get_project` |
| `/api/projects/{id}` | PUT | `routers/projects.py` | `update_project()` | FR-PROJ-004 | Required | `test_projects.py::test_update_project` |
| `/api/projects/{id}` | DELETE | `routers/projects.py` | `delete_project()` | FR-PROJ-005 | Required | `test_projects.py::test_delete_project` |
| `/api/projects/{id}/lifecycle` | PATCH | `routers/projects.py` | `bulk_lifecycle()` | FR-PROJ-006 | Admin | - |
| `/api/projects/{id}/positions` | GET | `routers/positions.py` | `list_project_positions()` | FR-POS-002 | Required | `test_projects.py::test_list_positions` |
| `/api/projects/{id}/positions` | POST | `routers/positions.py` | `create_position()` | FR-POS-001 | Required | `test_projects.py::test_create_position` |
| `/api/positions` | GET | `routers/positions.py` | `list_positions()` | FR-POS-002 | Required | `test_projects.py::test_list_positions` |
| `/api/positions/{id}` | GET | `routers/positions.py` | `get_position()` | FR-POS-003 | Required | `test_projects.py::test_get_position` |
| `/api/positions/{id}` | PUT | `routers/positions.py` | `update_position()` | FR-POS-004 | Required | `test_projects.py::test_update_position` |
| `/api/positions/{id}` | DELETE | `routers/positions.py` | `delete_position()` | FR-POS-005 | Required | `test_projects.py::test_delete_position` |
| `/api/candidates` | GET | `routers/candidates.py` | `list_candidates()` | FR-CAND-002 | Required | `test_candidates.py::test_list_candidates` |
| `/api/candidates` | POST | `routers/candidates.py` | `create_candidate()` | FR-CAND-001 | Required | `test_candidates.py::test_create_candidate` |
| `/api/candidates/{id}` | GET | `routers/candidates.py` | `get_candidate()` | FR-CAND-003 | Required | `test_candidates.py::test_get_candidate` |
| `/api/candidates/{id}` | PUT | `routers/candidates.py` | `update_candidate()` | FR-CAND-004 | Required | `test_candidates.py::test_update_candidate` |
| `/api/candidates/{id}` | PATCH | `routers/candidates.py` | `partial_update_candidate()` | FR-CAND-004 | Required | - |
| `/api/candidates/{id}` | DELETE | `routers/candidates.py` | `delete_candidate()` | FR-CAND-005 | Required | `test_candidates.py::test_delete_candidate` |
| `/api/candidates/bulk` | POST | `routers/candidates.py` | `bulk_candidates()` | FR-CAND-006 | Required | - |
| `/api/candidates/bulk-action` | POST | `routers/candidates.py` | `bulk_action()` | FR-CAND-006 | Required | - |
| `/api/candidates/import` | POST | `routers/candidates.py` | `import_candidates()` | FR-CAND-007 | Required | - |
| `/api/candidates/export` | GET | `routers/candidates.py` | `export_candidates()` | FR-CAND-008 | Required | - |
| `/api/ai/screen-candidate` | POST | `routers/ai.py` | `screen_candidate()` | FR-AI-001 | Required | `test_ai_integrations.py::test_cv_screening` |
| `/api/ai/analyze-file` | POST | `routers/ai.py` | `analyze_file()` | FR-AI-002 | Required | `test_ai_integrations.py::test_analyze_file` |
| `/api/ai/generate-jd` | POST | `routers/ai.py` | `generate_jd()` | FR-AI-003 | Required | `test_ai_integrations.py::test_jd_generation` |
| `/api/ai/generate-email` | POST | `routers/ai.py` | `generate_email()` | FR-AI-007 | Required | - |
| `/api/ai/call-script` | POST | `routers/ai.py` | `generate_call_script()` | FR-AI-008 | Required | - |
| `/api/ai/source-candidates` | POST | `routers/ai.py` | `source_candidates()` | FR-SRC-001 | Required | - |
| `/api/research/market-analysis` | POST | `routers/research.py` | `market_analysis()` | FR-AI-004 | Required | `test_ai_integrations.py::test_market_research` |
| `/api/research/salary-benchmark` | POST | `routers/research.py` | `salary_benchmark()` | FR-AI-005 | Required | `test_ai_integrations.py::test_salary_benchmark` |
| `/api/chatbot` | POST | `routers/ai.py` | `chatbot()` | FR-AI-009 | Required | `test_chatbot.py` |
| `/api/sourcing/overview` | GET | `routers/sourcing.py` | `sourcing_overview()` | FR-SRC-004 | Required | - |
| `/api/sourcing/linkedin-xray` | POST | `routers/sourcing.py` | `linkedin_xray()` | FR-SRC-001 | Required | - |
| `/api/sourcing/smartrecruiters-bulk` | POST | `routers/sourcing.py` | `smartrecruiters_bulk()` | FR-SRC-002 | Required | `test_smartrecruiters_integration.py` |
| `/api/sourcing/{job_id}/status` | GET | `routers/sourcing.py` | `sourcing_status()` | FR-SRC-003 | Required | - |
| `/api/documents` | GET | `routers/documents.py` | `list_documents()` | FR-DOC-002 | Required | - |
| `/api/documents/upload` | POST | `routers/documents.py` | `upload_document()` | FR-DOC-001 | Required | - |
| `/api/documents/{id}` | GET | `routers/documents.py` | `get_document()` | FR-DOC-003 | Required | - |
| `/api/documents/{id}/download` | GET | `routers/documents.py` | `download_document()` | FR-DOC-003 | Required | - |
| `/api/documents/{id}` | DELETE | `routers/documents.py` | `delete_document()` | FR-DOC-004 | Required | - |
| `/api/interviews` | GET | `routers/interviews.py` | `list_interviews()` | FR-INT-002 | Required | `test_interviews.py::test_list_interviews` |
| `/api/interviews` | POST | `routers/interviews.py` | `create_interview()` | FR-INT-001 | Required | `test_interviews.py::test_create_interview` |
| `/api/interviews/{id}` | PUT | `routers/interviews.py` | `update_interview()` | FR-INT-003 | Required | `test_interviews.py::test_update_interview` |
| `/api/interviews/{id}` | DELETE | `routers/interviews.py` | `delete_interview()` | FR-INT-004 | Required | `test_interviews.py::test_delete_interview` |
| `/api/activity` | GET | `routers/activity.py` | `get_activity()` | FR-ACT-002 | Required | `test_activity_security.py::test_activity_feed` |
| `/api/activity/stream` | GET | `routers/activity.py` | `stream_activity()` | FR-ACT-003 | Required | - |
| `/api/activity/dashboard/stats` | GET | `routers/activity.py` | `dashboard_stats()` | FR-REP-001 | Required | - |
| `/api/reporting/overview` | GET | `routers/reporting.py` | `reporting_overview()` | FR-REP-002 | Required | - |
| `/api/admin/users` | GET | `routers/admin.py` | `list_users()` | FR-ADM-001 | Admin | - |
| `/api/admin/users/{id}/role` | POST | `routers/admin.py` | `change_role()` | FR-ADM-001 | Admin | - |
| `/api/admin/activity` | GET | `routers/admin.py` | `admin_activity()` | FR-ACT-002 | Admin | - |
| `/api/admin/migrate-from-json` | POST | `routers/admin.py` | `migrate_from_json()` | FR-ADM-004 | Admin | - |
| `/api/admin/advanced/features` | GET | `routers/admin.py` | `get_features()` | FR-ADM-003 | Admin | - |
| `/api/admin/advanced/features/{key}` | PUT | `routers/admin.py` | `update_feature()` | FR-ADM-003 | Admin | - |
| `/api/admin/advanced/embeddings` | GET | `routers/admin.py` | `list_embeddings()` | Future | Admin | - |
| `/api/admin/advanced/embeddings` | POST | `routers/admin.py` | `create_embedding()` | Future | Admin | - |
| `/api/settings` | GET | `routers/settings.py` | `get_settings()` | FR-ADM-002 | Required | - |
| `/api/settings` | POST | `routers/settings.py` | `update_settings()` | FR-ADM-002 | Required | - |
| `/api/health` | GET | `routers/system.py` | `health_check()` | FR-ADM-005 | None | `test_health.py::test_health` |
| `/api/version` | GET | `routers/system.py` | `version_info()` | FR-ADM-006 | None | `test_health.py::test_version` |

---

## Test Coverage Matrix

### Test Files and Coverage

| Test File | Requirements Covered | Coverage % | Critical Paths | Status |
|-----------|----------------------|------------|----------------|--------|
| `test_auth.py` | FR-AUTH-001 to FR-AUTH-005<br>FR-ADM-001<br>SR-001 to SR-003 | 85% | ✓ Registration<br>✓ Login<br>✓ Token validation<br>✓ Password change<br>✓ RBAC | ✓ |
| `test_projects.py` | FR-PROJ-001 to FR-PROJ-006<br>FR-POS-001 to FR-POS-005 | 80% | ✓ CRUD operations<br>✓ Access control<br>✓ Position management | ✓ |
| `test_candidates.py` | FR-CAND-001 to FR-CAND-006 | 75% | ✓ CRUD operations<br>✓ Status tracking<br>✓ Soft delete<br>✓ Bulk operations | ✓ |
| `test_ai_integrations.py` | FR-AI-001 to FR-AI-006<br>IR-001 | 70% | ✓ CV screening<br>✓ JD generation<br>✓ Market research<br>✓ Salary benchmark<br>✓ Fallback logic | ✓ |
| `test_gemini_parsing.py` | FR-AI-001, FR-AI-002 | 65% | ✓ Screening format<br>✓ Document parsing<br>✓ Error handling | ✓ |
| `test_chatbot.py` | FR-AI-009 | 60% | ✓ Conversation flow<br>✓ Session management<br>✓ Tool suggestions | ✓ |
| `test_smartrecruiters_integration.py` | FR-SRC-002, IR-003 | 55% | ✓ Login<br>✓ Scraping<br>✓ Error handling | ✓ |
| `test_interviews.py` | FR-INT-001 to FR-INT-004 | 70% | ✓ Scheduling<br>✓ Update<br>✓ Cancel | ✓ |
| `test_activity_security.py` | FR-ACT-001 to FR-ACT-002<br>SR-007 | 80% | ✓ Logging<br>✓ Feed display<br>✓ Security | ✓ |
| `test_health.py` | FR-ADM-005, FR-ADM-006 | 90% | ✓ Health check<br>✓ Version info | ✓ |

### Coverage Gaps (To Be Addressed)

| Area | Missing Tests | Priority | Planned Sprint |
|------|---------------|----------|----------------|
| Document Upload/Download | FR-DOC-001, FR-DOC-003 | Medium | Sprint 3 |
| Candidate Import/Export | FR-CAND-007, FR-CAND-008 | Medium | Sprint 3 |
| LinkedIn Sourcing | FR-SRC-001 | Low | Sprint 4 |
| Real-Time SSE | FR-ACT-003 | Low | Sprint 4 |
| Bulk Project Operations | FR-PROJ-006 | Low | Sprint 4 |
| Admin Bulk Migration | FR-ADM-004 | Low | Sprint 5 |
| Feature Flags | FR-ADM-003 | Low | Sprint 5 |
| Email/Call Script Generation | FR-AI-007, FR-AI-008 | Low | Sprint 5 |

---

## Implementation Status Summary

### Feature Completion

| Category | Total Requirements | Implemented | Partial | Not Implemented | Completion % |
|----------|-------------------|-------------|---------|-----------------|--------------|
| **Business Requirements** | 10 | 10 | 0 | 0 | 100% |
| **Authentication & Authorization** | 5 | 5 | 0 | 0 | 100% |
| **Project Management** | 6 | 6 | 0 | 0 | 100% |
| **Position Management** | 5 | 5 | 0 | 0 | 100% |
| **Candidate Management** | 8 | 8 | 0 | 0 | 100% |
| **AI Features** | 10 | 10 | 0 | 0 | 100% |
| **Candidate Sourcing** | 4 | 4 | 0 | 0 | 100% |
| **Document Management** | 4 | 4 | 0 | 0 | 100% |
| **Interview Management** | 4 | 4 | 0 | 0 | 100% |
| **Activity & Reporting** | 5 | 5 | 0 | 0 | 100% |
| **Administration** | 6 | 6 | 0 | 0 | 100% |
| **Non-Functional** | 20 | 16 | 4 | 0 | 80% |

### Overall Project Status

- **Total Requirements:** 87
- **Fully Implemented:** 83 (95.4%)
- **Partially Implemented:** 4 (4.6%)
- **Not Implemented:** 0 (0%)

**Overall Completion:** 95.4%

---

## Requirements Change Log

| Version | Date | Requirement ID | Change Description | Approved By |
|---------|------|----------------|-------------------|-------------|
| 1.0 | 2025-11-25 | All | Initial requirements baseline | Product Owner |

---

**Document Approval:**

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Product Owner | [Name] | ___________ | ________ |
| Lead Developer | [Name] | ___________ | ________ |
| QA Lead | [Name] | ___________ | ________ |

---

**End of Traceability Matrix**
