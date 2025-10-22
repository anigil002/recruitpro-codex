# RecruitPro — Comprehensive System Documentation (v2.5, **Markdown Edition**)

**Last Updated:** 22 Oct 2025  
**Model:** **Gemini 2.5 Flash Lite**  
**Runtime:** **Python backend** (local API & workers) + **JavaScript frontend** (local SPA)  
**Scope:** End-to-end architecture, triggers, AI prompts, **SmartRecruiters web automation**, **complete database schema** (mandatory fields, PK/FK, indices), **Chatbot**, **Advanced AI Features**, **Email/Call generators**, **Salary Benchmark**, **Admin tools**, full **API table**, **UI/UX Design Philosophy**, and reusable **screening & outreach prompts**.

---

## 0) Changelog (since v2.4)
- Added **RecruitPro UI/UX Design Philosophy** section (full manifesto).
- Added **Verbal Screening Script prompt** (Egis format) and **Outreach email templates**.
- Kept all technical architecture, endpoints, database schema, prompts, and flows from prior versions consolidated into this single document.

---

## 1) System Overview

RecruitPro is a local-first ATS + AI platform that automates the recruitment lifecycle while keeping **humans in control**:

- **File → Intelligence:** Upload DOCX/PDF/TXT/**XLSX** → Gemini parses **project info** & **positions**; inserts positions as **draft**.  
- **Project Market Research (once):** If project info is detected and no research exists, a **highly agentic** market research job runs for **regional similar projects** (past 5 years + ongoing).  
- **AI Sourcing:** LinkedIn/Google X-Ray + optional SmartRecruiters (SR) **web automation** (no SR API), normalization, scoring.  
- **AI Screening:** CV parsing & multi-factor scoring vs JD.  
- **Comms Copilots:** Personalized **email** and **call** scripts.  
- **RecruitPro Chatbot:** Contextual Q&A + procedural copiloting.  
- **Analytics & Reporting:** KPIs, activity feed, logs.  
- **Admin Utilities:** migrations, DB optimization.

> **Compliance Note (SmartRecruiters):** Any browser automation must comply with SR Terms of Service, privacy rules, and applicable laws. Use your own credentials, avoid evasion tactics, and prefer official APIs if permitted.

---

## 2) Architecture & Components

| Component | Description |
|---|---|
| **Frontend** | `templates/recruitpro_ats.html` + vanilla JS modules (local SPA) |
| **Backend API (Python)** | FastAPI/Flask style app exposing `/api/*` |
| **Job Workers** | Python workers (RQ/Celery/Threads) for AI tasks & web automation |
| **Optional Node Helpers** | Small utilities for headless browsing/X-Ray |
| **AI Service** | **Gemini 2.5 Flash Lite** (JSON-first extraction & drafting) |
| **DB** | SQLite (local) or Supabase (cloud) |
| **Storage** | Local FS or Supabase buckets |
| **Realtime** | SSE/WebSocket for activity & job progress |
| **Advanced AI Module** | `advanced_ai_features.py` — feature toggles, prompt packs, embeddings refs |

---

## 3) Events & Triggers

| Trigger | When | Action | Result |
|---|---|---|---|
| **onFileUploaded** | POST `/api/projects/<id>/documents` | Worker calls **Gemini 2.5 Flash Lite** | a) Positions created (incl. from **Excel**) as **draft** b) Project metadata updated |
| **onProjectIntelDetected** | After analysis, if summary/region/client detected **and** no research exists | Launch **Market Research (once per project)** | Writes `project_market_research` (status → `completed`) |
| **onAISourcingStart** | POST `/api/ai/source-candidates` | Boolean/X-Ray + Google CSE + optional SR web automation | New `ai-sourced` candidates; job tracked |
| **onAIScreenCandidate** | POST `/api/ai/screen-candidate` | CV parse + multi-factor scoring | Score JSON saved; status advances |
| **onGenerateJD** | POST `/api/ai/generate-jd` | AI JD drafting | JD saved to `positions.description` |
| **onChatbotPrompt** | POST `/api/chatbot` | Retrieve session context + run prompt | Chat response + session log |
| **onSalaryBenchmark** | POST `/api/research/salary-benchmark` | Grounded wage research + cache | Salary ranges saved to `salary_benchmarks` |
| **onMigration** | POST `/api/admin/migrate-from-json` | Validate → stage → import | New/updated rows + migration log |

**Idempotency**  
- Market Research: once per project (`projects.research_done = 1`).  
- Positions: dedupe `(project_id, normalized_title, normalized_location)`.

---

## 4) AI Prompts (Gemini 2.5 Flash Lite)

### 4.1 File Analysis (DOCX/PDF/TXT/**XLSX**)
**System**
```
You are RecruitPro AI running on Gemini 2.5 Flash Lite. Extract project details and job positions from recruiter-uploaded files. Output strictly valid JSON following the given schema. If an Excel is provided, identify worksheets that list positions and parse rows as positions.
```

**User**
```
Analyze this file and return:
1) project_info (if present): name, summary, sector, location_region, client
2) positions: title, department, experience, responsibilities[], requirements[], location, description
3) file_diagnostics: { type: "docx|pdf|txt|xlsx", positions_detected: int, project_info_detected: boolean }

Schema:
{
  "project_info": {
    "name": "string|null",
    "summary": "string|null",
    "sector": "string|null",
    "location_region": "string|null",
    "client": "string|null"
  },
  "positions": [
    {
      "title": "string",
      "department": "string|null",
      "experience": "string|null",
      "responsibilities": ["string"],
      "requirements": ["string"],
      "location": "string|null",
      "description": "string|null"
    }
  ],
  "file_diagnostics": {
    "type": "string",
    "positions_detected": 0,
    "project_info_detected": false
  }
}

Notes:
- If Excel, parse sheets with headers such as [Title, Department, Experience, Location, Skills/Requirements].
- Deduplicate positions by normalized title + location.
- No commentary. Only JSON.
File URL: <FILE_URL>
```

### 4.2 Market Research (Once per Project, Grounded)
**System**
```
You are RecruitPro's market research agent. Use grounded web search results to build a factual list of similar projects in the same region. Prefer official client, PMC, consultant, and contractor sources. Output only JSON.
```

**User**
```
Project region: <REGION>. Sector: <SECTOR>. Summary: <SUMMARY>.
Find similar projects started or finished within the last 5 years, or ongoing now, in the same region.
Return up to 15 high-confidence matches with:
project_name, brief_details, project_location, start_date, completion_date,
client, pmo_pmc, pmcm, supervision_consultant, design_consultant,
architect, other_consultants[], contractor
+ sources[{title,url}]
Rules: grounded facts only; unknown → null; only JSON.
```

### 4.3 Generate JD (from Excel row or title)
**System**
```
You are RecruitPro JD writer. Create concise, ATS-friendly job descriptions with responsibilities and requirements aligned to AEC best practices and the given project/role context.
```

**User**
```
Title: <TITLE>
Department: <DEPT|null>
Experience: <EXP|null>
Location: <LOC|null>
Project Sector: <SECTOR|null>
Key skills/notes: <NOTES>

Return:
{"description":"...", "responsibilities":[...], "requirements":[...], "nice_to_have":[...]}
Only JSON.
```

### 4.4 Chatbot (Multi-tool, Context-aware)
**System**
```
You are the RecruitPro Chatbot. Be concise, accurate, and action-oriented.
Tools you can suggest (do not auto-run):
- Query projects/positions/candidates/interviews
- Generate outreach emails or call scripts
- Summarize CVs vs a position
- Show KPIs and recent activity
When user asks about system actions, return a brief, structured answer and, if relevant, propose one-click actions that correspond to existing endpoints (do not fabricate endpoints).
Maintain session memory: goals, entities (project/position/candidate), locale, and preferences.
Output plain text unless asked for JSON.
```

### 4.5 Generate Email (Personalized outreach)
**System**
```
You are a recruitment outreach assistant. Write short, personalized, high-conversion emails that sound professional and human.
```

**User**
```
Context:
- Position: <TITLE>, <LOCATION>, <SENIORITY>, key skills <SKILLS>
- Candidate: <NAME>, current title <CUR_TITLE>, highlights <HIGHLIGHTS>
- Company & Project: <COMPANY>, <PROJECT_SUMMARY>

Constraints:
- 120-180 words, crisp subject line, 2 short paragraphs + CTA.
- No placeholders; avoid hype; respect seniority; include location/remote notes.
- Return JSON only: {"subject":"...","body":"..."}
```

### 4.6 Call Script (Structured phone guide)
**System**
```
You create structured, respectful recruiter call scripts with objections handling.
```

**User**
```
Role: <TITLE>, Location: <LOCATION>, Candidate: <NAME>, Key value props: <POINTS>
Return JSON only:
{
 "opening": "30-second opener",
 "qualify": ["3-5 targeted questions"],
 "value_props": ["3 bullets"],
 "objections": [{"concern":"...", "response":"..."}],
 "closing": "CTA + next step"
}
```

### 4.7 Salary Benchmark (Grounded + cached)
**System**
```
You are a salary benchmarking assistant. Use grounded sources for the specified role and region. Provide a realistic range with a brief rationale and references.
```

**User**
```
Role: <TITLE>, Region: <REGION>, Sector: <SECTOR>, Seniority: <LEVEL>
Return JSON:
{
 "currency": "ISO code",
 "annual_min": number,
 "annual_mid": number,
 "annual_max": number,
 "rationale": "brief",
 "sources": [{"title":"", "url":""}]
}
Rules: Use region-specific data; if unavailable, use nearest reliable proxy (mark proxy=true).
```

---

## 5) SmartRecruiters Web Automation (No API)

**Flow:** Credentials modal → headless login → candidate search UI → apply filters → capture permitted fields → normalize & ingest as `ai-sourced` → logout & purge session.  
**Endpoints:** `35 /api/ai/source-candidates` (platforms includes `"smartrecruiters"`), `44 /api/smartrecruiters/bulk` (optional batching), `43 /api/sourcing/jobs/<id>` for progress.  
**Security:** Never log secrets; ephemeral storage; comply with ToS; conservative pacing; explicit user consent checkbox.

---

## 6) API Endpoints Usage Table (Full)

> Base table preserved; **two additions**: **53** `/api/ai/analyze-file` and **54** `/api/ai/generate-jd`.

|#|Endpoint|Method|Called From (Frontend Location)|Function/Component Name|
|---|---|---|---|---|
|**AUTHENTICATION & USER MANAGEMENT**|||||
|1|`/api/auth/register`|POST|`register.html`|Registration form submission|
|2|`/api/auth/login`|POST|`login.html`|Login form submission|
|3|`/api/auth/logout`|POST|`recruitpro_ats.html`|Logout button click|
|4|`/api/auth/change-password`|POST|`recruitpro_ats.html`|Settings page - password change form|
|5|`/api/user`|GET|`recruitpro_ats.html`|Dashboard initialization, profile display|
|6|`/api/user/profile`|PUT|`recruitpro_ats.html`|Settings page - profile edit form|
|7|`/api/user/settings`|PUT|`recruitpro_ats.html`|Settings page - preferences form|
|**DASHBOARD & ANALYTICS**|||||
|8|`/api/dashboard/stats`|GET|`recruitpro_ats.html`|`loadDashboard()`|
|9|`/api/activity`|GET|`recruitpro_ats.html`|Activity feed component|
|**PROJECT MANAGEMENT**|||||
|10|`/api/projects`|GET|`recruitpro_ats.html`|`loadProjects()`|
|11|`/api/projects`|POST|`recruitpro_ats.html`|`createProject()`|
|12|`/api/projects/<id>`|GET|`recruitpro_ats.html`|`viewProject(projectId)`, `editProject(projectId)`|
|13|`/api/projects/<id>`|PUT|`recruitpro_ats.html`|`updateProject(event, projectId)`|
|14|`/api/projects/<id>`|DELETE|`recruitpro_ats.html`|`deleteProject(projectId)`|
|15|`/api/projects/<id>/documents`|POST|`recruitpro_ats.html`|`uploadDocumentToProject(event, projectId)` **(triggers analysis)**|
|**POSITION MANAGEMENT**|||||
|16|`/api/positions`|GET|`recruitpro_ats.html`|`loadPositions()`|
|17|`/api/positions`|POST|`recruitpro_ats.html`|Create position form submission|
|18|`/api/positions/<id>`|GET|`recruitpro_ats.html`|`viewPosition`, `editPosition`|
|19|`/api/positions/<id>`|PUT|`recruitpro_ats.html`|Position edit form submission|
|20|`/api/positions/<id>`|DELETE|`recruitpro_ats.html`|Position delete button|
|**CANDIDATE MANAGEMENT**|||||
|21|`/api/candidates`|GET|`recruitpro_ats.html`|`loadCandidates()`|
|22|`/api/candidates`|POST|`recruitpro_ats.html`|Add candidate form submission|
|23|`/api/candidates/<id>`|GET|`recruitpro_ats.html`|`viewCandidate`|
|24|`/api/candidates/<id>`|PUT|`recruitpro_ats.html`|Candidate edit form submission|
|25|`/api/candidates/<id>`|PATCH|`recruitpro_ats.html`|Kanban drag & drop, quick edits|
|26|`/api/candidates/<id>`|DELETE|`recruitpro_ats.html`|Delete candidate|
|27|`/api/candidates/bulk-action`|POST|`recruitpro_ats.html`|Bulk toolbar actions|
|**DOCUMENT MANAGEMENT**|||||
|28|`/api/documents`|GET|`recruitpro_ats.html`|`loadDocuments()`|
|29|`/api/documents/upload`|POST|`recruitpro_ats.html`|File upload forms|
|30|`/api/documents/<id>/download`|GET|`recruitpro_ats.html`|`downloadDocument(...)` ⚠️ **BROKEN**|
|31|`/api/documents/<id>/view`|GET|`recruitpro_ats.html`|`viewDocument(docId)`|
|32|`/api/documents/<id>/file`|GET|`recruitpro_ats.html`|Referenced but ❌ **MISSING**|
|33|`/api/documents/<id>`|GET|`recruitpro_ats.html`|Document metadata retrieval|
|34|`/api/documents/<id>`|DELETE|`recruitpro_ats.html`|Delete document|
|**AI & SOURCING FEATURES**|||||
|35|`/api/ai/source-candidates`|POST|`recruitpro_ats.html`|`startAISourcing()` (LinkedIn/Google/SR)|
|36|`/api/ai/screen-candidate`|POST|`recruitpro_ats.html`|Screen candidate|
|37|`/api/ai/generate-email`|POST|`recruitpro_ats.html`|Email generator|
|38|`/api/ai/call-script`|POST|`recruitpro_ats.html`|Call script generator|
|39|`/api/chatbot`|POST|`recruitpro_ats.html`|Chatbot interface (RecruitProChatbot)|
|40|`/api/research/market-analysis`|POST|`recruitpro_ats.html`|Research tools panel (**programmatic once/project**)|
|41|`/api/research/salary-benchmark`|POST|`recruitpro_ats.html`|Salary research tools|
|42|`/api/sourcing/linkedin-xray/start`|POST|`recruitpro_ats.html`|LinkedIn sourcing panel|
|43|`/api/sourcing/jobs/<id>`|GET|`recruitpro_ats.html`|Auto-poll sourcing job status|
|44|`/api/smartrecruiters/bulk`|POST|`recruitpro_ats.html`|SR integration panel (web automation job)|
|**INTERVIEWS**|||||
|45|`/api/interviews`|GET|`recruitpro_ats.html`|Interviews page load|
|46|`/api/interviews`|POST|`recruitpro_ats.html`|Schedule interview|
|47|`/api/interviews/<id>`|PUT|`recruitpro_ats.html`|Interview feedback|
|**ADMIN ROUTES**|||||
|48|`/api/admin/users`|GET|`recruitpro_ats.html`|Admin user management|
|49|`/api/admin/migrate-from-json`|POST|`recruitpro_ats.html`|Admin migration tool|
|50|`/api/admin/database/optimize`|POST|`recruitpro_ats.html`|Admin DB tools|
|**HEALTH & MONITORING**|||||
|51|`/api/health`|GET|External monitoring|Health check|
|52|`/api/version`|GET|`recruitpro_ats.html`|About page|
|**ADDED (Internal/Optional)**|||||
|53|`/api/ai/analyze-file`|POST|Internal (called by #15 handler)|AI file analysis (Gemini parse)|
|54|`/api/ai/generate-jd`|POST|`recruitpro_ats.html`|Generate JD for a position|

**Status Summary:** **Total** 54 | **Working** 52 | **Broken** 1 (`/api/documents/<id>/download`) | **Missing** 1 (`/api/documents/<id>/file`)  

---

## 7) Database Schema (SQLite-compatible DDL)

> Mandatory columns are **NOT NULL**. Enable FK enforcement: `PRAGMA foreign_keys = ON;`

### 7.1 Core Tables
- `users`, `projects`, `project_documents`, `positions`, `candidates`,  
  `candidate_status_history`, `ai_jobs`, `sourcing_jobs`, `sourcing_results`,  
  `screening_runs`, `project_market_research`, `interviews`, `activity_feed`, `documents`

```sql
-- USERS
CREATE TABLE IF NOT EXISTS users (
  user_id        TEXT PRIMARY KEY,
  email          TEXT NOT NULL,
  password_hash  TEXT NOT NULL,
  name           TEXT NOT NULL,
  role           TEXT NOT NULL CHECK (role IN ('recruiter','admin')),
  settings       TEXT,
  created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users (LOWER(email));

-- PROJECTS
CREATE TABLE IF NOT EXISTS projects (
  project_id        TEXT PRIMARY KEY,
  name              TEXT NOT NULL,
  sector            TEXT,
  location_region   TEXT,
  summary           TEXT,
  client            TEXT,
  research_done     INTEGER NOT NULL DEFAULT 0,
  research_status   TEXT CHECK (research_status IN ('pending','in_progress','completed','failed')),
  created_by        TEXT NOT NULL,
  created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_projects_created_by ON projects (created_by);
CREATE INDEX IF NOT EXISTS idx_projects_region ON projects (location_region);

-- PROJECT DOCUMENTS
CREATE TABLE IF NOT EXISTS project_documents (
  doc_id        TEXT PRIMARY KEY,
  project_id    TEXT NOT NULL,
  filename      TEXT NOT NULL,
  file_url      TEXT NOT NULL,
  mime_type     TEXT NOT NULL,
  uploaded_by   TEXT NOT NULL,
  uploaded_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE,
  FOREIGN KEY (uploaded_by) REFERENCES users(user_id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_project_documents_project ON project_documents (project_id);

-- POSITIONS
CREATE TABLE IF NOT EXISTS positions (
  position_id      TEXT PRIMARY KEY,
  project_id       TEXT NOT NULL,
  title            TEXT NOT NULL,
  department       TEXT,
  experience       TEXT,
  responsibilities TEXT,
  requirements     TEXT,
  location         TEXT,
  description      TEXT,
  status           TEXT NOT NULL CHECK (status IN ('draft','open','closed')) DEFAULT 'draft',
  created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_positions_project_title_loc
  ON positions (project_id, LOWER(title), COALESCE(LOWER(location), ''));
CREATE INDEX IF NOT EXISTS idx_positions_project ON positions (project_id);

-- CANDIDATES
CREATE TABLE IF NOT EXISTS candidates (
  candidate_id   TEXT PRIMARY KEY,
  project_id     TEXT,
  position_id    TEXT,
  name           TEXT NOT NULL,
  email          TEXT,
  phone          TEXT,
  source         TEXT NOT NULL CHECK (source IN ('manual','ai-sourced','referral','linkedin','github','job-board','smartrecruiters')),
  status         TEXT NOT NULL CHECK (status IN ('new','screening','interviewing','offer','hired','rejected','withdrawn')) DEFAULT 'new',
  rating         INTEGER CHECK (rating BETWEEN 1 AND 5),
  resume_url     TEXT,
  ai_score       TEXT,
  created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE SET NULL,
  FOREIGN KEY (position_id) REFERENCES positions(position_id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_candidates_position ON candidates (position_id);
CREATE INDEX IF NOT EXISTS idx_candidates_project ON candidates (project_id);
CREATE INDEX IF NOT EXISTS idx_candidates_status ON candidates (status);

-- CANDIDATE STATUS HISTORY
CREATE TABLE IF NOT EXISTS candidate_status_history (
  history_id    TEXT PRIMARY KEY,
  candidate_id  TEXT NOT NULL,
  old_status    TEXT,
  new_status    TEXT NOT NULL,
  changed_by    TEXT NOT NULL,
  changed_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (candidate_id) REFERENCES candidates(candidate_id) ON DELETE CASCADE,
  FOREIGN KEY (changed_by) REFERENCES users(user_id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_cand_status_hist_cand ON candidate_status_history (candidate_id);

-- AI JOBS
CREATE TABLE IF NOT EXISTS ai_jobs (
  job_id        TEXT PRIMARY KEY,
  job_type      TEXT NOT NULL CHECK (job_type IN ('file_analysis','market_research','ai_sourcing','ai_screening','generate_jd')),
  project_id    TEXT,
  position_id   TEXT,
  candidate_id  TEXT,
  status        TEXT NOT NULL CHECK (status IN ('pending','in_progress','completed','failed')) DEFAULT 'pending',
  request_json  TEXT,
  response_json TEXT,
  error         TEXT,
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    DATETIME
);
CREATE INDEX IF NOT EXISTS idx_ai_jobs_project ON ai_jobs (project_id);
CREATE INDEX IF NOT EXISTS idx_ai_jobs_type_status ON ai_jobs (job_type, status);

-- SOURCING JOBS
CREATE TABLE IF NOT EXISTS sourcing_jobs (
  sourcing_job_id TEXT PRIMARY KEY,
  project_id      TEXT NOT NULL,
  position_id     TEXT NOT NULL,
  params_json     TEXT NOT NULL,
  status          TEXT NOT NULL CHECK (status IN ('pending','in_progress','completed','failed')) DEFAULT 'pending',
  progress        INTEGER NOT NULL DEFAULT 0,
  found_count     INTEGER NOT NULL DEFAULT 0,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME,
  FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE,
  FOREIGN KEY (position_id) REFERENCES positions(position_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_sourcing_jobs_pos ON sourcing_jobs (position_id);

-- SOURCING RESULTS
CREATE TABLE IF NOT EXISTS sourcing_results (
  result_id       TEXT PRIMARY KEY,
  sourcing_job_id TEXT NOT NULL,
  platform        TEXT NOT NULL,
  profile_url     TEXT NOT NULL,
  name            TEXT,
  title           TEXT,
  company         TEXT,
  location        TEXT,
  summary         TEXT,
  quality_score   REAL,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (sourcing_job_id) REFERENCES sourcing_jobs(sourcing_job_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_src_results_job ON sourcing_results (sourcing_job_id);
CREATE UNIQUE INDEX IF NOT EXISTS ux_src_results_profile_per_job ON sourcing_results (sourcing_job_id, profile_url);

-- SCREENING RUNS
CREATE TABLE IF NOT EXISTS screening_runs (
  screening_id  TEXT PRIMARY KEY,
  candidate_id  TEXT NOT NULL,
  position_id   TEXT NOT NULL,
  score_json    TEXT NOT NULL,
  notes         TEXT,
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (candidate_id) REFERENCES candidates(candidate_id) ON DELETE CASCADE,
  FOREIGN KEY (position_id) REFERENCES positions(position_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_screening_runs_cand ON screening_runs (candidate_id);
CREATE INDEX IF NOT EXISTS idx_screening_runs_pos ON screening_runs (position_id);

-- PROJECT MARKET RESEARCH
CREATE TABLE IF NOT EXISTS project_market_research (
  research_id   TEXT PRIMARY KEY,
  project_id    TEXT NOT NULL,
  region        TEXT NOT NULL,
  window        TEXT NOT NULL,
  findings      TEXT NOT NULL,
  sources       TEXT NOT NULL,
  status        TEXT NOT NULL CHECK (status IN ('pending','in_progress','completed','failed')) DEFAULT 'completed',
  error         TEXT,
  started_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  completed_at  DATETIME,
  FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_research_once_per_project ON project_market_research (project_id);

-- INTERVIEWS
CREATE TABLE IF NOT EXISTS interviews (
  interview_id   TEXT PRIMARY KEY,
  project_id     TEXT,
  position_id    TEXT NOT NULL,
  candidate_id   TEXT NOT NULL,
  scheduled_at   DATETIME NOT NULL,
  location       TEXT,
  mode           TEXT CHECK (mode IN ('onsite','remote','hybrid')),
  notes          TEXT,
  feedback       TEXT,
  updated_by     TEXT,
  updated_at     DATETIME,
  created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE SET NULL,
  FOREIGN KEY (position_id) REFERENCES positions(position_id) ON DELETE CASCADE,
  FOREIGN KEY (candidate_id) REFERENCES candidates(candidate_id) ON DELETE CASCADE,
  FOREIGN KEY (updated_by) REFERENCES users(user_id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_interviews_position ON interviews (position_id);
CREATE INDEX IF NOT EXISTS idx_interviews_candidate ON interviews (candidate_id);

-- ACTIVITY FEED
CREATE TABLE IF NOT EXISTS activity_feed (
  activity_id  TEXT PRIMARY KEY,
  actor_type   TEXT NOT NULL CHECK (actor_type IN ('system','ai','user')),
  actor_id     TEXT,
  project_id   TEXT,
  position_id  TEXT,
  candidate_id TEXT,
  event_type   TEXT NOT NULL,
  message      TEXT NOT NULL,
  created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE SET NULL,
  FOREIGN KEY (position_id) REFERENCES positions(position_id) ON DELETE SET NULL,
  FOREIGN KEY (candidate_id) REFERENCES candidates(candidate_id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_activity_project ON activity_feed (project_id, created_at DESC);

-- DOCUMENTS
CREATE TABLE IF NOT EXISTS documents (
  id           TEXT PRIMARY KEY,
  filename     TEXT NOT NULL,
  file_url     TEXT NOT NULL,
  mime_type    TEXT NOT NULL,
  owner_user   TEXT,
  scope        TEXT NOT NULL CHECK (scope IN ('project','candidate','global')),
  scope_id     TEXT,
  uploaded_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (owner_user) REFERENCES users(user_id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_documents_scope ON documents (scope, scope_id);
```

### 7.2 Chatbot Tables
```sql
CREATE TABLE IF NOT EXISTS chatbot_sessions (
  session_id   TEXT PRIMARY KEY,
  user_id      TEXT NOT NULL,
  context_json TEXT,
  created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at   DATETIME,
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_chatbot_sessions_user ON chatbot_sessions (user_id);

CREATE TABLE IF NOT EXISTS chatbot_messages (
  message_id   TEXT PRIMARY KEY,
  session_id   TEXT NOT NULL,
  role         TEXT NOT NULL CHECK (role IN ('user','assistant','system')),
  content      TEXT NOT NULL,
  created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES chatbot_sessions(session_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_chatbot_messages_session ON chatbot_messages (session_id, created_at);
```

### 7.3 Comms Generators (Email & Call)
```sql
CREATE TABLE IF NOT EXISTS communication_templates (
  template_id   TEXT PRIMARY KEY,
  type          TEXT NOT NULL CHECK (type IN ('email','call_script')),
  name          TEXT NOT NULL,
  template_json TEXT NOT NULL,
  created_by    TEXT NOT NULL,
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS outreach_runs (
  outreach_id   TEXT PRIMARY KEY,
  user_id       TEXT NOT NULL,
  candidate_id  TEXT,
  position_id   TEXT,
  type          TEXT NOT NULL CHECK (type IN ('email','call_script')),
  output_json   TEXT NOT NULL,
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL,
  FOREIGN KEY (candidate_id) REFERENCES candidates(candidate_id) ON DELETE SET NULL,
  FOREIGN KEY (position_id) REFERENCES positions(position_id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_outreach_runs_user ON outreach_runs (user_id, created_at DESC);
```

### 7.4 Salary Benchmarking
```sql
CREATE TABLE IF NOT EXISTS salary_benchmarks (
  benchmark_id  TEXT PRIMARY KEY,
  title         TEXT NOT NULL,
  region        TEXT NOT NULL,
  sector        TEXT,
  seniority     TEXT,
  currency      TEXT NOT NULL,
  annual_min    REAL NOT NULL,
  annual_mid    REAL NOT NULL,
  annual_max    REAL NOT NULL,
  rationale     TEXT,
  sources       TEXT NOT NULL,
  created_by    TEXT NOT NULL,
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_salary_benchmarks_key ON salary_benchmarks (LOWER(title), LOWER(region), LOWER(COALESCE(sector,'')), LOWER(COALESCE(seniority,'')));
```

### 7.5 Advanced AI Features
```sql
CREATE TABLE IF NOT EXISTS advanced_features_config (
  key          TEXT PRIMARY KEY,
  value_json   TEXT NOT NULL,
  updated_by   TEXT,
  updated_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (updated_by) REFERENCES users(user_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS embeddings_index_refs (
  index_id     TEXT PRIMARY KEY,
  name         TEXT NOT NULL,
  description  TEXT,
  vector_dim   INTEGER NOT NULL,
  location_uri TEXT NOT NULL,
  created_by   TEXT,
  created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE SET NULL
);
```

### 7.6 Admin Tools (Migrations & Optimization)
```sql
CREATE TABLE IF NOT EXISTS admin_migration_logs (
  migration_id  TEXT PRIMARY KEY,
  user_id       TEXT NOT NULL,
  source_name   TEXT NOT NULL,
  items_total   INTEGER NOT NULL,
  items_success INTEGER NOT NULL,
  items_failed  INTEGER NOT NULL,
  error_json    TEXT,
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_admin_migration_logs_user ON admin_migration_logs (user_id, created_at DESC);
```

---

## 8) Operational Flows (Python Pseudocode Summary)

```python
# POST /api/projects/<id>/documents
def upload_document(project_id, file, generate_jd=False):
    url = storage.save(project_id, file)
    activity.log(project_id, "file_uploaded", f"Uploaded {file.filename}")
    enqueue(analyze_file_job, project_id, url, generate_jd)
    return {"status": "queued", "file_url": url}

def analyze_file_job(project_id, file_url, generate_jd):
    ai = Gemini(model="gemini-2.5-flash-lite", temperature=0.15)
    result = ai.analyze_file(file_url)  # prompt 4.1

    # 1) project info → market research (once)
    if result["project_info"] and any(result["project_info"].values()):
        update_project_with_ai_intel(project_id, result["project_info"])
        proj = db.get_project(project_id)
        if proj.research_done == 0:
            db.insert_ai_job('market_research', project_id, status='pending')
            enqueue(run_market_research_job, project_id, proj.location_region, proj.sector, proj.summary)

    # 2) positions
    for pos in dedupe_positions(project_id, result["positions"]):
        pid = db.insert_or_ignore_position(project_id, pos, status="draft")
        if generate_jd and pid:
            enqueue(generate_jd_job, pid, pos)

    activity.log(project_id, "positions_created", f"Detected {len(result['positions'])} position(s)")

def run_market_research_job(project_id, region, sector, summary):
    db.set_project_research_status(project_id, 'in_progress')
    ai = Gemini(model="gemini-2.5-flash-lite", temperature=0.15)
    findings = ai.market_research(region, sector, summary)  # prompt 4.2
    db.insert_project_research(project_id, region, findings)
    db.mark_project_research_done(project_id)
    activity.log(project_id, "market_research_completed", "Research written to insights")

def generate_jd_job(position_id, pos_hint):
    ai = Gemini(model="gemini-2.5-flash-lite", temperature=0.2)
    jd = ai.generate_jd(pos_hint)  # prompt 4.3
    db.update_position_with_jd(position_id, jd)

# Chatbot
def chatbot_endpoint(payload, user_id):
    session_id = payload.get("session_id") or create_session(user_id)
    save_user_message(session_id, payload["message"])
    context = load_session_context(session_id)
    tools_hint = discover_relevant_tools(payload["message"], context)
    reply = gemini.chat(system=CHATBOT_SYSTEM, user=compose_user_msg(payload["message"], context, tools_hint))
    save_assistant_message(session_id, reply.text)
    return {"session_id": session_id, "reply": reply.text, "tools_suggested": tools_hint}

# Email & Call
def generate_email_endpoint(body, user_id):
    ctx = hydrate_context(body)
    resp = gemini.json_prompt(system=EMAIL_SYS, user=mk_email_user(ctx))
    save_outreach_run(user_id=user_id, type='email', output_json=resp.json())
    return resp.json()

def call_script_endpoint(body, user_id):
    ctx = hydrate_context(body)
    resp = gemini.json_prompt(system=CALL_SYS, user=mk_call_user(ctx))
    save_outreach_run(user_id=user_id, type='call_script', output_json=resp.json())
    return resp.json()

# Salary Benchmark
def salary_benchmark_endpoint(body, user_id):
    resp = gemini.json_prompt(system=SALARY_SYS, user=mk_salary_user(body))
    db.insert_salary_benchmark(resp["title"], resp["region"], resp.get("sector"),
        resp.get("seniority"), resp["currency"], resp["annual_min"], resp["annual_mid"],
        resp["annual_max"], resp.get("rationale"), json.dumps(resp["sources"]), created_by=user_id)
    return resp
```

---

## 9) UI/UX — Design Philosophy (Full Manifesto)

### *Professional Recruitment Platform Design Manifesto*

#### 9.1 CORE DESIGN PHILOSOPHY — Human-in-the-Loop AI Partnership
AI augments, humans decide. AI is embedded in workflows, recruiters retain agency.

#### 9.2 FOUNDATIONAL PRINCIPLES

**AI Transparency & Trust**
- Actor Attribution (🤖 AI / ⚙️ System / 👤 User)
- Visible AI Progress
- Explainable Recommendations
- Manual Override

**Project-Centric Information Architecture**
```
Organization
  └─ Projects (hiring initiatives)
       ├─ Positions (job openings)
       ├─ Candidates (talent pool)
       ├─ Documents (knowledge base)
       └─ Market Research (competitive intelligence)
```

**Progressive Disclosure**
- Dashboard → Lists → Details → Modals → Expandables

**Efficiency via Intelligent Defaults**
- Auto-population on upload
- AI JD suggestions
- Predictive sourcing (boolean/X-Ray)
- One-click bulk actions
- Template reuse

**Real-Time Feedback & Awareness**
- WebSockets, toasts, activity feed, status badges, progress bars

**Data Density Without Clutter**
- Card layouts, white space, typography, iconography, color coding

#### 9.3 VISUAL DESIGN SYSTEM
- **Colors:** #062C3A primary, #00617E teal, #ABC100 lime, #F4A41D orange, #C8313F red, #71164C purple, neutrals #5D858B/#97B8BB  
- **Typography:** System stack, 32/24/18/16/14 scale; 1.5–1.6 body LH  
- **Grid:** 8pt spacing; 240px sidebar; 1400px content max; card padding 24px  
- **Components:** Buttons (primary/secondary/ghost), Inputs (focus ring), Cards (elevation), Tables (striped, hover)

#### 9.4 INTERACTION PATTERNS
- **Navigation:** Sidebar + Breadcrumbs + Global search (⌘K) + Recents + Quick Actions  
- **States:** Skeletons, spinners, progress; empty/error states with recovery  
- **Forms:** Inline edit, multi-step progress, smart autocomplete, validation  
- **Bulk Ops:** Checkbox selection → toolbar → action → confirmation → progress → summary

#### 9.5 SPECIALIZED INTERFACES
- **Kanban Pipeline:** New → Screening → Interview → Final Review → Offer  
- **AI Sourcing UI:** Position select, params, platforms, limits, AI enhancement; live progress sample block  
- **Candidate Profile:** Header + summary + tabs (overview/screening/activity/docs/notes/outreach) + action bar  
- **Dashboard:** 8 KPI cards + Activity feed + Quick actions

#### 9.6 RESPONSIVE & ACCESSIBILITY
- Desktop-first; tablet/mobile adaptations; 44×44 targets  
- WCAG 2.1 AA: contrast, keyboard, ARIA, reduced motion

#### 9.7 PERFORMANCE & GOVERNANCE
- Optimistic UI, skeletons, caching, debounce; lazy loading, pagination, code-splitting  
- Component library docs; semantic versioning; changelogs; A/B tests; quarterly audits

**Summary:** A professional, efficient, and transparent platform where AI enhances every interaction and recruiters remain in control.

---

## 10) Reusable Prompts — Screening & Outreach

### 10.1 Verbal Screening Script (Egis Format)

```
You are Abdulla Nigil, Regional Talent Acquisition Manager at Egis.

Generate a value-based verbal screening script following the Egis format below for the role: {ROLE_TITLE}, under the project or business unit: {PROJECT_NAME}, within the sector: {SECTOR_TYPE}.

---

### 1. Introduction
Always start with this exact introduction, using Abdulla Nigil’s real tone:

“Hi {candidate name}, thanks for taking the time to speak with me today.  
I’m Abdulla Nigil from the Talent Acquisition team at Egis.  

We’ve scheduled about 20 to 25 minutes to discuss the {ROLE_TITLE} role within {PROJECT_NAME}, explore how your experience aligns with what the team is looking for, and ensure it’s a role that genuinely fits your goals.  
Does that still work for you?”

---

### 2. Context & Consent

Always follow with this exact statement:

“Great. Just so you know, I’ll be taking a few notes as we go along to capture key points for the hiring team — is that alright with you?”  
(Wait for consent.)

---

### 3. Candidate Type – Applied vs. Sourced Flow

If the candidate applied directly:
“I’ve reviewed your background, but I’d love to hear from you directly — what parts of your experience do you think are most relevant to this role or project?”

If the candidate was sourced or may not know much about the role:
“I realize you may not have seen the job details yet, so let me start with a quick overview.”

Provide a short, tailored overview:
“This position is for a {ROLE_TITLE} within our {PROJECT_NAME}, which is part of Egis’s work in {SECTOR_TYPE}.  
The role involves {1–2 core responsibilities or focus areas}, and we’re looking for someone with experience in {relevant technical or managerial discipline}.  
It’s based in {location or setup}, and the role will work closely with {key stakeholders or team context}.  
Your experience in {matching skill or project area} caught my attention.”

Then transition:
“Before we go deeper, I’d love to hear what you’ve been focused on recently — and what kind of opportunity would be interesting enough for you to consider right now.”

---

### 4. Relevance & Alignment (4–5 min)

Generate 2–3 tailored questions that:
- Link the candidate’s background to the role/project context.
- Surface their transferable strengths.
- Avoid repetition or textbook phrasing.

---

### 5. Evidence of Impact (5–7 min)

Generate 2–3 role-specific probes to reveal measurable results, leadership behavior, and problem-solving examples.  
For example:
- Technical roles → systems, tools, design, interfaces, delivery.  
- Managerial roles → leadership, stakeholder management, KPIs, decision-making.  
- Commercial roles → cost, risk, contracts, claims, optimization.  
- Design roles → coordination, modeling, standards, approvals.

---

### 6. Motivation & Timing (4–5 min)

Include 2–3 questions that uncover:
- Why they’re considering a move now.  
- What they’re looking for in their next challenge.  
- What attracted them to Egis or this specific project.

---

### 7. Decision Enablers (3–4 min)

Include practical, respectful questions covering:
- Current compensation and expected range.  
- Notice period or start availability.  
- Willingness to relocate, travel, or work hybrid/project-based.

---

### 8. Closing (1–2 min)

Always end with this version:

“Thank you — this has been really helpful and gives me a clear sense of your background, motivations, and fit for the role.  
I’ll summarize our discussion and share it with the hiring team for review.  
Once they’ve had a look, I’ll come back to you with next steps.  

Before we wrap up — is there anything important you’d like me to highlight to the team, or any questions you have for me?”

---

### 9. Internal Notes Table

| **Category** | **Key Points / Observations** |
|---------------|-------------------------------|
| Relevance to role | |
| Key achievements | |
| Strengths / differentiators | |
| Motivation | |
| Availability / mobility | |
| Compensation expectations | |
| Notes to highlight to hiring team | |

---

Tone & Output Rules:
- Must sound natural, conversational, and confident — exactly how Abdulla Nigil speaks in real calls.
- Never include “generic” textbook filler (no “walk me through your CV” unless reframed with purpose).
- Always produce a polished, ready-to-use script formatted for spoken delivery.
```

### 10.2 First Outreach Email Templates (3 Variants)

**A. Standard Outreach (Most Roles)**

_Subject:_ `Opportunity with Egis – {Role Title}, {Project Name or Sector}`

_Message:_
```
Hi {candidate name},

I came across your profile and thought your background could align well with one of our ongoing opportunities at Egis.

We’re currently looking for a {role title} to join our {project or business unit}, which is part of Egis’s work in the {sector, e.g., transportation, infrastructure, aviation, etc.}. The role involves {1–2 key focus areas}, and I felt your experience in {relevant skill/project type} could be a strong match.

Would you be open to a quick 15–20 minute conversation this week to explore the role and see if it could be of interest?

Best regards,
Abdulla Nigil
Regional Talent Acquisition Manager
Egis Group
```

**B. Executive / Leadership Outreach**

_Subject:_ `Leadership Opportunity with Egis – {Role Title}, {Project Name}`

_Message:_
```
Hi {candidate name},

I wanted to reach out personally regarding a strategic leadership opportunity we’re currently recruiting for at Egis — the {role title} position for our {project name or business line}.

Given your leadership background in {relevant area/organization type}, I believe this could align closely with your experience and the impact we’re looking for in this role.

Egis continues to expand its presence in {sector/region}, and this position plays a pivotal role in shaping the success of that initiative.

Would you be open to a brief, confidential conversation to discuss the opportunity and your career goals?

Warm regards,
Abdulla Nigil
Regional Talent Acquisition Manager
Egis Group
```

**C. Technical / Project Specialist Outreach**

_Subject:_ `Egis Opportunity – {Role Title}, {Project Name or Sector}`

_Message:_
```
Hi {candidate name},

I came across your profile and was impressed by your background in {specific technical area or project type}.

We currently have an opening for a {role title} within our {project or program name} at Egis, part of our work in {sector}. The role involves {brief 1–2 line scope summary}, and your experience in {relevant systems, design, or delivery area} seems particularly relevant.

Would you be available for a short introductory chat to explore the fit and share more about what we’re building here at Egis?

Kind regards,
Abdulla Nigil
Regional Talent Acquisition Manager
Egis Group
```

**Optional closers (add as needed):**
- “If now isn’t the right time, I’d still appreciate connecting for future collaboration.”  
- “If this isn’t the right fit, feel free to refer a colleague who might be open to exploring.”  
- “I’ll be happy to share a quick brief or call invite if you’d like to learn more.”

**Automation-Ready Prompt**
```
Generate a first-outreach message (email/LinkedIn InMail) from Abdulla Nigil, Regional Talent Acquisition Manager at Egis, for the role {ROLE_TITLE} under {PROJECT_NAME} in the {SECTOR}. 
Tone: professional, concise, and personalized. 
Output 3 variants — standard, executive, and technical — following Egis branding and realistic recruiter voice.
```

---

## 11) Security & Monitoring

- Local-first; outbound only for sourcing/research.  
- JWT + RBAC; hashed passwords; no secret logging.  
- Rate-limit AI endpoints; transient error retry (1x).  
- Audit trails in `activity_feed`; `/api/health` & `/api/version` endpoints for probes.  
- SR compliance: consent checkbox, no evasion tactics, logout & purge session artifacts.

---

## 12) Completeness Checklist

- [x] Architecture, triggers, and flows  
- [x] AI prompts (analysis, research, JD, chatbot, email, call, salary)  
- [x] SmartRecruiters automation section  
- [x] Full API table (54 endpoints)  
- [x] Database schema (core + chatbot + comms + salary + advanced features + admin logs)  
- [x] Pseudocode flows  
- [x] UI/UX Design Philosophy (full)  
- [x] Reusable screening & outreach prompts

---

**End of Document**
