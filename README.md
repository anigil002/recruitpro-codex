# RecruitPro Application

**Status: Ready for Local Single-User Deployment**

This application is fully functional for local single-user deployment with SQLite. For production multi-user deployment, see [PRODUCTION_SETUP.md](PRODUCTION_SETUP.md) for additional configuration (PostgreSQL, Redis, etc.).

---

This repository provides an executable reference implementation of the RecruitPro ATS & AI platform described in `recruitpro_system_v2.5.md`. The goal is to make the documentation tangible by shipping a runnable FastAPI backend, lightweight HTML shell, and automated tests.

## Features

- FastAPI backend that exposes the 54 endpoints captured in the documentation.
- SQLite persistence layer with SQLAlchemy models mirroring the published schema (⚠️ PostgreSQL required for production).
- **AI integration** with Google Gemini (11 AI features implemented):
  - CV Screening with Egis-format compliance tables
  - Document Analysis (project info & position extraction)
  - Job Description Generation
  - Market Research & Salary Benchmarking
  - Candidate Scoring & Outreach Generation
  - Chatbot Assistant & Boolean Search
  - Fallback system for offline/development mode
- Activity feed logging, admin tools, and real-time event streaming.
- Minimal HTML front end (`templates/recruitpro_ats.html`) aligned with the UI design philosophy.
- Automated tests that exercise the health, version, and core auth flow.
- Cross-platform Electron desktop application that bundles the backend, renderer, and diagnostics required for production deploys.

## Getting Started

### 1. Install Dependencies

#### Python Dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -e .[dev]
```

If you prefer a non-editable install, use `python -m pip install .[dev]` instead.

#### Node.js Dependencies (for CSS)

The UI uses Tailwind CSS which needs to be compiled:

```bash
npm install
npm run build:css
```

For development with auto-rebuild on changes:

```bash
npm run watch:css
```

### 2. Configure Environment

#### Option A: Using Environment Variables

Set the required secrets and runtime configuration before starting the API:

```bash
export RECRUITPRO_SECRET_KEY="change-me"
export RECRUITPRO_DATABASE_URL="sqlite:///./data/recruitpro.db"
export RECRUITPRO_CORS_ALLOWED_ORIGINS="http://localhost:3000,http://localhost:8000"
```

#### Option B: Using .env File

Create a `.env` file to configure all options in one place:

1. Copy the template: `cp .env.example .env`
2. Edit values as needed
3. Restart the application

**For AI integration**, you can configure the Gemini API key either:
- **Via UI** (Recommended): Navigate to `/settings` after starting the app - no restart needed
- **Via .env**: Set `RECRUITPRO_GEMINI_API_KEY` in `.env` and restart

Get your API key from [Google AI Studio](https://aistudio.google.com/app/apikey).

**Without an API key**, RecruitPro runs in **fallback mode** using intelligent heuristics. See [`AI_INTEGRATION_GUIDE.md`](AI_INTEGRATION_GUIDE.md) for details.

### 3. Initialize the Database

Create the schema locally by running:

```bash
python -m app.database
```

### 4. Launch the API

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Visit `http://localhost:8000/docs` for the interactive Swagger UI and `http://localhost:8000/` for a simple status response.

### 5. Use the Local Console

Navigate to `http://localhost:8000/app` after signing into the API. The lightweight console lets you:

- Register or log in to a RecruitPro account stored in SQLite.
- Create projects, attach positions, and add candidates using the live REST endpoints.
- Refresh statistics and open a candidate profile page (which can also be accessed directly via `/candidate-profile?candidate_id=...&token=...`).

All data is persisted locally, so the UI can be used offline once the backend is running.

## Desktop Application (Electron)

The repository also ships with a cross-platform Electron shell that bundles the FastAPI backend and the HTML renderer. The desktop build starts the API server automatically, runs health checks, and launches the RecruitPro UI inside a native window. All feature areas called out in `recruitpro_system_v2.5.md` are wired into the renderer and backend so the desktop client mirrors the full web experience.

Refer to [`desktop/FEATURE_STATUS.md`](desktop/FEATURE_STATUS.md) for a live verification matrix that is updated whenever a capability is validated in the Electron shell.

### Prerequisites

- Node.js 18+
- npm 9+
- Python 3.11 with the RecruitPro dependencies installed (the Electron build reuses the backend from this repository)

### Install dependencies

```bash
cd desktop
npm install
```

### Run the desktop app in development

```bash
npm start
```

The Electron main process will spawn the FastAPI backend (using `python3 -m uvicorn app.main:app`) and wait for it to become available on `http://127.0.0.1:8000` before showing the window. To use a different Python interpreter or port, set the following environment variables before running the command:

```bash
export ELECTRON_PYTHON="/path/to/python"
export BACKEND_PORT=8010
```

### Package installers

Electron Builder is configured to produce installers for macOS (DMG), Windows (NSIS), and Linux (AppImage/Deb). To generate distributables, run:

```bash
npm run make
```

The packaged application includes the FastAPI source code and templates in the installer bundle. Ensure the target system has a compatible Python runtime and that dependencies from `pyproject.toml` are installed or vendored prior to distributing the build.

### Development Status

**⚠️ The Electron application is NOT production-ready.** Critical items pending:

- [ ] Database migration to PostgreSQL with connection pooling
- [ ] Background queue system (Redis + RQ) for async tasks
- [ ] Complete pagination for all list endpoints
- [ ] ClamAV virus scanning integration
- [ ] Rate limiting (per-user, per-endpoint)
- [ ] HTTPS redirect middleware
- [ ] Production monitoring (Sentry, Prometheus)
- [ ] Load testing with realistic scenarios
- [ ] Security audit completion
- [ ] Staging environment setup
- [ ] Backup and disaster recovery procedures

Document progress in [`desktop/FEATURE_STATUS.md`](desktop/FEATURE_STATUS.md) as items are completed.

### 6. Run Tests

```bash
pytest
```

The tests now cover authentication, project flows, AI helpers, and admin-protected activity endpoints.

### 4. Storage Directory

Uploaded documents are saved under the `storage/` directory, which is served statically at `/storage/*`.

## Project Structure

```
app/
  config.py        # Environment-aware settings
  database.py      # SQLAlchemy session management
  main.py          # FastAPI application factory
  models/          # SQLAlchemy ORM models aligned to the schema
  routers/         # Modular API routers grouped by domain
  services/        # Supporting services and AI stubs
  utils/           # Shared helpers (security, IDs)
templates/         # Minimal UI shell for RecruitPro
storage/           # Uploaded assets (gitignored)
recruitpro_system_v2.5.md  # Comprehensive product documentation
```

## AI Integration

RecruitPro features **AI integration** with Google's Gemini API (⚠️ background queue system required for production use).

### Quick Start

1. Get API key: [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Set in `.env`: `RECRUITPRO_GEMINI_API_KEY=your-key`
3. Restart application

### AI Features (All Implemented)

| Feature | Status | API Endpoint |
|---------|--------|--------------|
| CV Screening | ✅ Live | `POST /api/ai/screen-candidate` |
| Document Analysis | ✅ Live | `POST /api/ai/analyze-file` |
| JD Generation | ✅ Live | `POST /api/ai/generate-jd` |
| Market Research | ✅ Live | `POST /api/research/market-analysis` |
| Salary Benchmarking | ✅ Live | `POST /api/research/salary-benchmark` |
| Candidate Scoring | ✅ Live | `POST /api/ai/screen-candidate` |
| Outreach Generation | ✅ Live | `POST /api/ai/generate-email` |
| Call Scripts | ✅ Live | `POST /api/ai/call-script` |
| Chatbot | ✅ Live | `POST /api/chatbot` |
| Candidate Sourcing | ✅ Live | `POST /api/ai/source-candidates` |
| Boolean Search | ✅ Live | Integrated in sourcing |

### Fallback Mode

**Without an API key**, RecruitPro runs in **intelligent fallback mode**:
- Uses heuristic algorithms and templates
- Provides functional responses
- Never crashes or returns errors
- Perfect for development/testing

**With an API key**, RecruitPro uses **live Gemini AI**:
- Detailed, context-specific analyses
- Evidence-based reasoning
- Unique responses for each request
- Production-grade quality

📚 **Complete Documentation**: See [`AI_INTEGRATION_GUIDE.md`](AI_INTEGRATION_GUIDE.md) for architecture, testing, and deployment details.

## Notes

- **AI Integration is fully implemented** - Configure `RECRUITPRO_GEMINI_API_KEY` to enable live AI or run in fallback mode.
- Security-sensitive routes (admin, auth) apply role checks and hashed passwords. JWT tokens provide stateless authentication.
- The implementation intentionally favours clarity and developer experience to help future contributors extend the platform.
