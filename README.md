# RecruitPro Application

This repository provides an executable reference implementation of the RecruitPro ATS & AI platform described in `recruitpro_system_v2.5.md`. The goal is to make the documentation tangible by shipping a runnable FastAPI backend, lightweight HTML shell, and automated tests.

## Features

- FastAPI backend that exposes the 54 endpoints captured in the documentation with pragmatic stub logic.
- SQLite persistence layer with SQLAlchemy models mirroring the published schema.
- Deterministic AI helpers for file analysis, JD drafting, sourcing, screening, outreach, and salary benchmarking.
- Activity feed logging, admin tools, sourcing stubs, and chatbot placeholder.
- Minimal HTML front end (`templates/recruitpro_ats.html`) aligned with the UI design philosophy.
- Automated tests that exercise the health, version, and core auth flow.

## Getting Started

### 1. Install Dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -e .[dev]
```

If you prefer a non-editable install, use `python -m pip install .[dev]` instead.

### 2. Configure Environment

Set the required secrets and runtime configuration before starting the API:

```bash
export RECRUITPRO_SECRET_KEY="change-me"
export RECRUITPRO_DATABASE_URL="sqlite:///./data/recruitpro.db"
export RECRUITPRO_CORS_ALLOWED_ORIGINS="http://localhost:3000,http://localhost:8000"
```

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

The repository also ships with a cross-platform Electron shell that bundles the FastAPI backend and the HTML renderer. The desktop build starts the API server automatically and launches the RecruitPro UI inside a native window.

> **Feature coverage note:** The Electron renderer currently exposes only a subset of the workflows described in `recruitpro_system_v2.5.md`. Refer to [`desktop/FEATURE_STATUS.md`](desktop/FEATURE_STATUS.md) for a live matrix of which capability areas are implemented, partially implemented, or missing from the desktop experience. Use that document when planning new work to bring the shell to feature parity with the product specification.

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

## Notes

- AI-heavy endpoints use deterministic stub data so the system functions offline while matching documented behaviors.
- Security-sensitive routes (admin, auth) apply role checks and hashed passwords. JWT tokens provide stateless authentication.
- The implementation intentionally favours clarity and developer experience to help future contributors extend the platform.
