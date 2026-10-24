"""Canvas routes: grounding on LLM rewrites, honest failure on unparseable replies."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from src.api import app

RESUME = "- Built a REST API serving 10K requests/day\n- Led migration to microservices"


async def _post(path: str, body: dict):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        return await c.post(path, json=body)


@pytest.mark.asyncio
async def test_reoptimize_flags_invented_numbers(scripted_llm) -> None:
    scripted_llm.generate.return_value = "- Built a REST API serving 5M requests/day, cutting latency 40%"
    r = await _post("/api/v1/canvas/section/s1/reoptimize", {
        "section_id": "s1", "section_title": "Experience", "section_content": RESUME, "resume_text": RESUME,
    })
    data = r.json()["data"]
    assert r.status_code == 200
    assert data["grounding"]["flagged"] is True
    assert "40" in data["grounding"]["novel_numbers"]


@pytest.mark.asyncio
async def test_reoptimize_clean_rewrite_is_not_flagged(scripted_llm) -> None:
    scripted_llm.generate.return_value = "- Built a REST API serving 10K requests/day\n- Led the microservices migration"
    r = await _post("/api/v1/canvas/section/s1/reoptimize", {
        "section_id": "s1", "section_title": "Experience", "section_content": RESUME, "resume_text": RESUME,
    })
    assert r.json()["data"]["grounding"]["flagged"] is False


@pytest.mark.asyncio
async def test_enhance_returns_content_and_grounding(scripted_llm) -> None:
    scripted_llm.generate.return_value = "- Led a REST API serving 10K requests/day"
    r = await _post("/api/v1/canvas/section/s1/enhance", {
        "section_id": "s1", "section_title": "Experience", "prompt": "more leadership",
        "section_content": RESUME, "resume_text": RESUME,
    })
    data = r.json()["data"]
    assert data["enhanced_content"].startswith("- Led")
    assert data["grounding"]["flagged"] is False


@pytest.mark.asyncio
async def test_dispute_unparseable_reply_is_an_error_not_a_default_score(scripted_llm) -> None:
    scripted_llm.generate.return_value = "I think the bullet is fine."
    r = await _post("/api/v1/canvas/dispute/b1", {
        "bullet_text": "Built a REST API", "user_disagreement": "It is good", "resume_text": RESUME,
    })
    assert r.status_code == 502


@pytest.mark.asyncio
async def test_dispute_discards_rewrite_that_invents_a_number(scripted_llm) -> None:
    scripted_llm.generate.return_value = (
        "SCORE: 0.8\nBULLET: Built a REST API serving 99M users\nRATIONALE: Stronger with scale."
    )
    r = await _post("/api/v1/canvas/dispute/b1", {
        "bullet_text": "Built a REST API", "user_disagreement": "needs scale", "resume_text": RESUME,
    })
    data = r.json()["data"]
    assert r.status_code == 200
    assert data["revised_bullet"] == "Built a REST API"
    assert "discarded" in data["provenance"]["decision_rationale"]
    assert data["provenance"]["agent_name"] == "DisputeReview"


@pytest.mark.asyncio
async def test_linkedin_refresh_without_connection_reports_not_connected() -> None:
    r = await _post("/api/v1/canvas/profile/linkedin/refresh", {})
    data = r.json()["data"]
    assert data["connected"] is False
    assert data["items"] == []
