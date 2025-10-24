import pytest

from app.services.ai import background_queue
from app.services.gemini import GeminiService, gemini


@pytest.mark.parametrize("service", [gemini, GeminiService()])
def test_gemini_uses_flash_lite_latest(service):
    assert service.model == GeminiService.DEFAULT_MODEL == "gemini-flash-lite-latest"


def test_background_queue_has_expected_ai_triggers():
    handlers = background_queue.registered_job_types()
    expected = {
        "file_analysis",
        "market_research",
        "ai_sourcing",
        "linkedin_xray",
        "smartrecruiters_bulk",
    }
    assert expected.issubset(set(handlers))
