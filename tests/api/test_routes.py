"""Optimize / alignment / health / auth routes."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.api import app
from src.config.settings import settings

RESUME = "Python developer with 5 years experience building REST APIs and PostgreSQL databases."
JD = "Senior Backend Engineer with Python FastAPI PostgreSQL experience required."


def client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_optimize_returns_job_id_immediately_and_stores_result(fake_redis) -> None:
    fake_pipeline = MagicMock()
    fake_pipeline.run = AsyncMock(return_value={"optimized_content": "x", "metrics": {}, "warnings": []})
    with patch("src.pipeline.Pipeline", return_value=fake_pipeline), patch("src.llm.client.LLMClient"):
        async with client() as c:
            r = await c.post("/api/v1/optimize", json={"resume_text": RESUME, "job_description": JD})
            job_id = r.json()["data"]["job_id"]
            assert r.status_code == 200
            for _ in range(50):  # background task
                await asyncio.sleep(0.02)
                stored = json.loads(fake_redis.kv[f"job:{job_id}"])
                if stored["status"] != "running":
                    break
            res = await c.get(f"/api/v1/optimize/{job_id}/result")
    assert stored["status"] == "completed"
    assert res.json()["data"]["optimized_content"] == "x"


@pytest.mark.asyncio
async def test_optimize_failure_is_recorded_and_surfaced(fake_redis) -> None:
    fake_pipeline = MagicMock()
    fake_pipeline.run = AsyncMock(side_effect=RuntimeError("model unreachable"))
    with patch("src.pipeline.Pipeline", return_value=fake_pipeline), patch("src.llm.client.LLMClient"):
        async with client() as c:
            r = await c.post("/api/v1/optimize", json={"resume_text": RESUME, "job_description": JD})
            job_id = r.json()["data"]["job_id"]
            for _ in range(50):
                await asyncio.sleep(0.02)
                if json.loads(fake_redis.kv[f"job:{job_id}"])["status"] != "running":
                    break
            res = await c.get(f"/api/v1/optimize/{job_id}/result")
    assert res.json()["status"] == "error"
    assert "model unreachable" in res.json()["error"]["message"]
    assert any("PIPELINE_ERROR" in m for _, m in fake_redis.published)


@pytest.mark.asyncio
async def test_optimize_rejects_short_input() -> None:
    async with client() as c:
        r = await c.post("/api/v1/optimize", json={"resume_text": "Short", "job_description": "Also short"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_status_of_unknown_job(fake_redis) -> None:
    async with client() as c:
        r = await c.get("/api/v1/optimize/nope/status")
    assert r.json()["data"]["job_status"] == "not_found"


@pytest.mark.asyncio
async def test_alignment_score_endpoint() -> None:
    result = MagicMock(overall_score=0.75, gaps=["python"], section_scores={"content": 0.75})
    with patch("src.rag.embedder.Embedder"), patch("src.scoring.alignment.AlignmentScorer") as scorer:
        scorer.return_value.score.return_value = result
        async with client() as c:
            r = await c.post("/api/v1/alignment/score", json={"resume_text": RESUME, "job_description": JD})
    assert r.status_code == 200
    assert r.json()["data"]["overall_score"] == 0.75


@pytest.mark.asyncio
async def test_health_is_open_and_reports_config(monkeypatch) -> None:
    monkeypatch.setattr(settings, "api_secret_key", "s3cret")
    async with client() as c:
        r = await c.get("/health")
    assert r.status_code == 200
    assert r.json()["auth_required"] is True


@pytest.mark.asyncio
async def test_api_requires_key_when_configured(monkeypatch, fake_redis) -> None:
    monkeypatch.setattr(settings, "api_secret_key", "s3cret")
    async with client() as c:
        no_key = await c.get("/api/v1/optimize/x/status")
        bad = await c.get("/api/v1/optimize/x/status", headers={"X-API-Key": "wrong"})
        good = await c.get("/api/v1/optimize/x/status", headers={"X-API-Key": "s3cret"})
        preflight = await c.options(
            "/api/v1/optimize", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"}
        )
    assert no_key.status_code == 401
    assert bad.status_code == 401
    assert good.status_code == 200
    assert preflight.status_code == 200


@pytest.mark.asyncio
async def test_api_open_without_key_configured(monkeypatch, fake_redis) -> None:
    monkeypatch.setattr(settings, "api_secret_key", "")
    async with client() as c:
        r = await c.get("/api/v1/optimize/x/status")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_app_shell_is_open_but_api_is_guarded(monkeypatch, tmp_path) -> None:
    """With a key set, the SPA must still load (to show the key screen) while /api stays locked."""
    from src.api import _mount_frontend, create_app

    (tmp_path / "index.html").write_text("<html>shell</html>")
    (tmp_path / "app.js").write_text("console.log(1)")
    monkeypatch.setattr(settings, "api_secret_key", "s3cret")
    monkeypatch.setattr(settings, "frontend_dist", str(tmp_path))
    app2 = create_app()
    async with AsyncClient(transport=ASGITransport(app=app2), base_url="http://test") as c:
        assert "shell" in (await c.get("/canvas/abc")).text          # SPA fallback for deep links
        assert (await c.get("/app.js")).text.startswith("console")
        assert (await c.get("/api/v1/optimize/x/status")).status_code == 401
        assert (await c.get("/../../etc/passwd")).status_code in (200, 404)  # never a file outside dist
        assert "root:" not in (await c.get("/%2e%2e/%2e%2e/etc/passwd")).text
