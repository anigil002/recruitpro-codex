"""SmartRecruiters automation and candidate import helpers."""

from __future__ import annotations

import re
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urljoin

from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import Candidate, Position, Project
from ..utils.security import generate_id
from .activity import log_activity
from .integrations import get_integration_value

try:  # pragma: no cover - optional heavy dependency
    from playwright.sync_api import (  # type: ignore
        TimeoutError as PlaywrightTimeoutError,
        Locator,
        Page,
        sync_playwright,
    )
except ImportError:  # pragma: no cover - executed when playwright is unavailable
    PlaywrightTimeoutError = TimeoutError  # type: ignore[assignment]
    Locator = Page = None  # type: ignore
    sync_playwright = None


STATUS_KEYWORDS: Sequence[Tuple[str, Sequence[str]]] = (
    ("hired", ("hired", "hire", "accepted offer")),
    ("offer", ("offer", "offered")),
    ("interview", ("interview", "interviewing")),
    ("screening", ("screen", "screening", "phone screen")),
    ("rejected", ("reject", "rejected", "declined", "disqualified")),
    ("archived", ("archive", "archived")),
)


class SmartRecruitersError(RuntimeError):
    """Base exception for SmartRecruiters automation failures."""


class SmartRecruitersConfigError(SmartRecruitersError):
    """Raised when SmartRecruiters integration is misconfigured."""


class SmartRecruitersLoginError(SmartRecruitersError):
    """Raised when the automation is unable to authenticate."""


class SmartRecruitersScrapeError(SmartRecruitersError):
    """Raised when candidate data could not be extracted."""


@dataclass(slots=True)
class SmartRecruitersCandidate:
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[str] = None
    stage: Optional[str] = None
    location: Optional[str] = None
    profile_url: Optional[str] = None
    resume_url: Optional[str] = None
    tags: List[str] = field(default_factory=list)


@dataclass(slots=True)
class SmartRecruitersJob:
    position_id: str
    job_url: Optional[str] = None
    job_id: Optional[str] = None
    filters: Optional[Dict[str, object]] = None


class SmartRecruitersClient:
    """Thin Playwright client used to scrape SmartRecruiters candidate lists."""

    def __init__(
        self,
        *,
        email: str,
        password: str,
        base_url: str,
        headless: bool = True,
    ) -> None:
        self._email = email
        self._password = password
        self._base_url = base_url.rstrip("/") + "/"
        self._headless = headless
        self._play = None
        self._browser = None
        self._context = None
        self._page: Optional[Page] = None

    def __enter__(self) -> "SmartRecruitersClient":
        if sync_playwright is None:  # pragma: no cover - safeguards optional dependency
            raise SmartRecruitersConfigError("Playwright is not installed. Install playwright to enable SmartRecruiters automation.")
        self._play = sync_playwright().start()
        self._browser = self._play.chromium.launch(headless=self._headless)
        self._context = self._browser.new_context()
        self._page = self._context.new_page()
        self._authenticate()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._play:
            self._play.stop()
        self._page = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def fetch_candidates(self, job: SmartRecruitersJob) -> List[SmartRecruitersCandidate]:
        page = self._require_page()
        target_url = self._job_url(job)
        try:
            page.goto(target_url, wait_until="domcontentloaded")
            page.wait_for_load_state("networkidle")
        except PlaywrightTimeoutError as exc:  # pragma: no cover - relies on remote system
            raise SmartRecruitersScrapeError(f"Timed out loading SmartRecruiters job page {target_url}") from exc

        if job.filters:
            self._apply_filters(page, job.filters)

        candidates = self._extract_candidates(page)
        if not candidates:
            raise SmartRecruitersScrapeError("No candidates located on SmartRecruiters job page")
        return candidates

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _authenticate(self) -> None:
        page = self._require_page()
        login_url = urljoin(self._base_url, "signin")
        try:
            page.goto(login_url, wait_until="domcontentloaded")
            page.wait_for_selector("input[type='email']")
            page.fill("input[type='email']", self._email)
            submit_selector = "button[type='submit'], button:has-text('Next')"
            page.click(submit_selector)
            page.wait_for_selector("input[type='password']")
            page.fill("input[type='password']", self._password)
            page.click("button[type='submit'], button:has-text('Sign in')")
            page.wait_for_load_state("networkidle")
        except PlaywrightTimeoutError as exc:  # pragma: no cover - real browser behaviour
            raise SmartRecruitersLoginError("Timed out while attempting to authenticate with SmartRecruiters") from exc

        error_banner = page.locator("text=Invalid username or password")
        if error_banner.count():  # pragma: no cover - depends on UI feedback
            raise SmartRecruitersLoginError("SmartRecruiters rejected the provided credentials")

    def _apply_filters(self, page: Page, filters: Dict[str, object]) -> None:
        status = filters.get("status")
        stage = filters.get("stage")
        if status:
            self._click_filter(page, str(status))
        if stage and stage != status:
            self._click_filter(page, str(stage))

    def _click_filter(self, page: Page, label: str) -> None:
        locator = page.locator(f"button:has-text('{label}')")
        if locator.count():
            locator.first.click()
            page.wait_for_timeout(300)

    def _extract_candidates(self, page: Page) -> List[SmartRecruitersCandidate]:
        cards = page.locator("[data-qa='candidate-card'], [data-test='candidate-card'], article.candidate")
        if not cards.count():
            rows = page.locator("table tbody tr")
            if rows.count():
                return [self._candidate_from_row(rows.nth(i)) for i in range(rows.count())]
            return []
        return [self._candidate_from_card(cards.nth(i)) for i in range(cards.count())]

    def _candidate_from_card(self, element: Locator) -> SmartRecruitersCandidate:
        name = self._first_text(element, ["a[data-qa='candidate-name']", "a[data-test='candidate-name']", "[data-qa='candidate-card'] h3", "h3"])
        details = element.inner_text()
        email = self._first_attribute(element, "a[href^='mailto:']", "href")
        phone = self._first_attribute(element, "a[href^='tel:']", "href")
        profile_url = self._first_attribute(element, "a[data-qa='candidate-name']", "href")
        status = self._first_text(element, ["[data-qa='application-status']", "[data-test='application-status']", ".status", ".stage"])
        stage = self._first_text(element, ["[data-qa='stage-label']", "[data-test='stage-label']", ".stage", ".pipeline-stage"])
        location = self._first_text(element, ["[data-qa='candidate-location']", ".location"])
        resume_url = self._first_attribute(element, "a:has-text('Resume')", "href")
        email = _clean_contact(email)
        phone = _clean_contact(phone)
        tags = _extract_tags(details)
        return SmartRecruitersCandidate(
            name=name or "Unknown Candidate",
            email=email,
            phone=phone,
            status=status or stage,
            stage=stage or status,
            location=location,
            profile_url=profile_url,
            resume_url=resume_url,
            tags=tags,
        )

    def _candidate_from_row(self, element: Locator) -> SmartRecruitersCandidate:
        text = element.inner_text()
        links = element.locator("a")
        email = None
        profile_url = None
        resume_url = None
        for i in range(links.count()):
            link = links.nth(i)
            href = link.get_attribute("href")
            if not href:
                continue
            if href.startswith("mailto:"):
                email = href
            elif href.startswith("tel:"):
                continue
            elif "resume" in href.lower():
                resume_url = href
            else:
                profile_url = href
        name = links.first.inner_text() if links.count() else text.split("\n")[0]
        status = None
        parts = [part.strip() for part in text.split("\n") if part.strip()]
        if len(parts) > 1:
            status = parts[1]
        email = _clean_contact(email)
        return SmartRecruitersCandidate(
            name=name,
            email=email,
            status=status,
            stage=status,
            profile_url=profile_url,
            resume_url=resume_url,
            tags=_extract_tags(text),
        )

    def _require_page(self) -> Page:
        if not self._page:
            raise SmartRecruitersScrapeError("SmartRecruiters browser context is not initialised")
        return self._page

    def _job_url(self, job: SmartRecruitersJob) -> str:
        if job.job_url:
            return job.job_url
        if not job.job_id:
            raise SmartRecruitersConfigError("SmartRecruiters job configuration missing job_url and job_id")
        settings = get_settings()
        company_id = settings.smartrecruiters_company_id
        if not company_id:
            raise SmartRecruitersConfigError("SMARTRECRUITERS_COMPANY_ID must be configured when using job_id")
        return urljoin(self._base_url, f"recruiter/company/{company_id}/jobs/{job.job_id}/candidates/list")

    def _first_text(self, element: Locator, selectors: Sequence[str]) -> Optional[str]:
        for selector in selectors:
            try:
                locator = element.locator(selector)
            except Exception:  # pragma: no cover - defensive
                continue
            if locator.count():
                text = locator.first.inner_text().strip()
                if text:
                    return text
        return None

    def _first_attribute(self, element: Locator, selector: str, attribute: str) -> Optional[str]:
        try:
            locator = element.locator(selector)
        except Exception:  # pragma: no cover - defensive
            return None
        if not locator.count():
            return None
        value = locator.first.get_attribute(attribute)
        return value


class SmartRecruitersImporter:
    """High level orchestration for importing SmartRecruiters candidates."""

    def __init__(self, client: SmartRecruitersClient) -> None:
        self._client = client

    def run(
        self,
        session: Session,
        *,
        project: Project,
        jobs: Iterable[SmartRecruitersJob],
        notes: Optional[str],
    ) -> Dict[str, object]:
        summary: Dict[str, object] = {
            "project_id": project.project_id,
            "imported": 0,
            "updated": 0,
            "skipped": 0,
            "jobs": [],
        }
        affected_projects: set[str] = set()
        affected_positions: set[str] = set()

        for job in jobs:
            result, project_ids, position_ids = self._import_job(session, project, job, notes)
            summary["imported"] += result["imported"]
            summary["updated"] += result["updated"]
            summary["skipped"] += result["skipped"]
            summary["jobs"].append(result)
            affected_projects.update(project_ids)
            affected_positions.update(position_ids)

        self._recalculate_metrics(session, affected_projects, affected_positions)
        if notes:
            summary["notes"] = notes
        return summary

    def _import_job(
        self,
        session: Session,
        project: Project,
        job: SmartRecruitersJob,
        notes: Optional[str],
    ) -> Tuple[Dict[str, object], set[str], set[str]]:
        position = session.get(Position, job.position_id)
        if not position:
            raise SmartRecruitersConfigError(f"Position {job.position_id} not found")
        if position.project_id != project.project_id:
            raise SmartRecruitersConfigError("Position does not belong to the specified project")

        candidates = self._client.fetch_candidates(job)
        job_summary: Dict[str, object] = {
            "position_id": position.position_id,
            "job_url": job.job_url or job.job_id,
            "imported": 0,
            "updated": 0,
            "skipped": 0,
            "candidates": [],
        }
        project_ids: set[str] = {project.project_id}
        position_ids: set[str] = {position.position_id}

        for record in candidates:
            outcome, candidate = self._persist_candidate(session, project, position, record, notes)
            if outcome == "created":
                job_summary["imported"] += 1
            elif outcome == "updated":
                job_summary["updated"] += 1
            else:
                job_summary["skipped"] += 1
            if candidate.project_id:
                project_ids.add(candidate.project_id)
            if candidate.position_id:
                position_ids.add(candidate.position_id)
            job_summary["candidates"].append(
                {
                    "candidate_id": candidate.candidate_id,
                    "name": candidate.name,
                    "status": candidate.status,
                    "outcome": outcome,
                }
            )
        return job_summary, project_ids, position_ids

    def _persist_candidate(
        self,
        session: Session,
        project: Project,
        position: Position,
        record: SmartRecruitersCandidate,
        notes: Optional[str],
    ) -> Tuple[str, Candidate]:
        candidate = self._find_existing_candidate(session, project, position, record)
        if candidate:
            changed = self._update_candidate(candidate, record, notes)
            session.add(candidate)
            outcome = "updated" if changed else "unchanged"
        else:
            candidate = self._create_candidate(session, project, position, record, notes)
            outcome = "created"
        session.flush()
        return outcome, candidate

    def _find_existing_candidate(
        self,
        session: Session,
        project: Project,
        position: Position,
        record: SmartRecruitersCandidate,
    ) -> Optional[Candidate]:
        if record.email:
            existing = (
                session.query(Candidate)
                .filter(
                    Candidate.project_id == project.project_id,
                    Candidate.email == record.email,
                )
                .first()
            )
            if existing:
                return existing
        if record.profile_url:
            existing = (
                session.query(Candidate)
                .filter(
                    Candidate.project_id == project.project_id,
                    Candidate.source == "smartrecruiters",
                    Candidate.resume_url == record.profile_url,
                )
                .first()
            )
            if existing:
                return existing
        return (
            session.query(Candidate)
            .filter(
                Candidate.project_id == project.project_id,
                Candidate.position_id == position.position_id,
                Candidate.name == record.name,
            )
            .first()
        )

    def _create_candidate(
        self,
        session: Session,
        project: Project,
        position: Position,
        record: SmartRecruitersCandidate,
        notes: Optional[str],
    ) -> Candidate:
        candidate = Candidate(
            candidate_id=generate_id(),
            project_id=project.project_id,
            position_id=position.position_id,
            name=record.name,
            email=record.email,
            phone=record.phone,
            source="smartrecruiters",
            status=_normalise_status(record.status or record.stage),
            resume_url=record.resume_url or record.profile_url,
            tags=_merge_tags(record.tags, notes),
            created_at=datetime.utcnow(),
        )
        session.add(candidate)
        log_activity(
            session,
            actor_type="ai",
            actor_id=None,
            project_id=project.project_id,
            position_id=position.position_id,
            candidate_id=candidate.candidate_id,
            message=f"Imported {candidate.name} from SmartRecruiters",
            event_type="smartrecruiters_import",
        )
        return candidate

    def _update_candidate(
        self,
        candidate: Candidate,
        record: SmartRecruitersCandidate,
        notes: Optional[str],
    ) -> bool:
        changed = False
        status = _normalise_status(record.status or record.stage)
        if status and status != candidate.status:
            candidate.status = status
            changed = True
        if record.email and record.email != candidate.email:
            candidate.email = record.email
            changed = True
        if record.phone and record.phone != candidate.phone:
            candidate.phone = record.phone
            changed = True
        if record.resume_url and record.resume_url != candidate.resume_url:
            candidate.resume_url = record.resume_url
            changed = True
        merged_tags = _merge_tags(record.tags, notes, existing=candidate.tags)
        if merged_tags != candidate.tags:
            candidate.tags = merged_tags
            changed = True
        return changed

    def _recalculate_metrics(
        self,
        session: Session,
        project_ids: Iterable[str],
        position_ids: Iterable[str],
    ) -> None:
        from ..models import Candidate as CandidateModel

        for project_id in project_ids:
            project = session.get(Project, project_id)
            if not project:
                continue
            hires = (
                session.query(CandidateModel)
                .filter(CandidateModel.project_id == project_id, CandidateModel.status == "hired")
                .count()
            )
            project.hires_count = hires
            session.add(project)
        for position_id in position_ids:
            position = session.get(Position, position_id)
            if not position:
                continue
            applicants = session.query(CandidateModel).filter(CandidateModel.position_id == position_id).count()
            position.applicants_count = applicants
            session.add(position)


def run_smartrecruiters_bulk(session: Session, request: Dict[str, object]) -> Dict[str, object]:
    """Execute a SmartRecruiters bulk import request."""

    email = get_integration_value("smartrecruiters_email", session=session)
    password = get_integration_value("smartrecruiters_password", session=session)
    settings = get_settings()
    if not email or not password:
        raise SmartRecruitersConfigError("SmartRecruiters credentials are not configured")

    project_id = request.get("project_id")
    if not project_id:
        raise SmartRecruitersConfigError("SmartRecruiters import requires a project_id")
    project = session.get(Project, project_id)
    if not project:
        raise SmartRecruitersConfigError("Project not found for SmartRecruiters import")

    raw_jobs = request.get("jobs")
    if not isinstance(raw_jobs, list) or not raw_jobs:
        raise SmartRecruitersConfigError("SmartRecruiters import requires at least one job configuration")

    notes = request.get("notes")
    jobs: List[SmartRecruitersJob] = []
    for entry in raw_jobs:
        if not isinstance(entry, dict):
            raise SmartRecruitersConfigError("Invalid SmartRecruiters job payload")
        job = SmartRecruitersJob(
            position_id=str(entry.get("position_id")),
            job_url=entry.get("job_url"),
            job_id=entry.get("job_id"),
            filters=entry.get("filters"),
        )
        jobs.append(job)

    headless = not bool(request.get("debug"))
    client = SmartRecruitersClient(
        email=email,
        password=password,
        base_url=settings.smartrecruiters_base_url,
        headless=headless,
    )
    importer = SmartRecruitersImporter(client)
    with client:
        summary = importer.run(session, project=project, jobs=jobs, notes=notes if isinstance(notes, str) else None)
    return summary


def _normalise_status(raw: Optional[str]) -> str:
    if not raw:
        return "new"
    lowered = raw.strip().lower()
    for status, keywords in STATUS_KEYWORDS:
        if any(keyword in lowered for keyword in keywords):
            return status
    return lowered.replace(" ", "_") or "new"


def _merge_tags(*tag_sources: Optional[Iterable[str]], existing: Optional[Iterable[str]] = None) -> Optional[List[str]]:
    tags = {"smartrecruiters"}
    tags.update(tag for source in tag_sources if source for tag in _coerce_tags(source))
    if existing:
        tags.update(tag for tag in existing if tag)
    if not tags:
        return None
    return sorted(tags)


def _coerce_tags(source: Iterable[str] | str) -> Iterable[str]:
    if isinstance(source, str):
        return [token.strip() for token in re.split(r"[,;]", source) if token.strip()]
    return [tag for tag in source if tag]


def _extract_tags(text: str) -> List[str]:
    matches = re.findall(r"#(\w+)", text)
    return sorted(set(matches))


def _clean_contact(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    value = value.strip()
    if value.startswith("mailto:"):
        return value.replace("mailto:", "", 1)
    if value.startswith("tel:"):
        return value.replace("tel:", "", 1)
    return value


__all__ = [
    "SmartRecruitersError",
    "SmartRecruitersConfigError",
    "SmartRecruitersClient",
    "SmartRecruitersImporter",
    "SmartRecruitersCandidate",
    "SmartRecruitersJob",
    "run_smartrecruiters_bulk",
]
