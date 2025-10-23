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
pip install pdm
pdm install
```

### 2. Launch the API

```bash
pdm run uvicorn app.main:app --reload
```

Visit `http://localhost:8000/docs` for the interactive Swagger UI and `http://localhost:8000/` for a simple status response.

### 3. Run Tests

```bash
pdm run pytest
```

The tests ensure critical endpoints (health, version, and auth flow) operate correctly.

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
