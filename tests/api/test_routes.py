"""Tests for API routes."""

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch, MagicMock, AsyncMock

from src.api import app


@pytest.mark.asyncio
async def test_optimize_endpoint():
    # Arrange
    transport = ASGITransport(app=app)

    # Act
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/optimize", json={
            "resume_text": "Experienced software engineer with 5 years of Python experience. Built REST APIs and microservices.",
            "job_description": "Senior Backend Engineer with Python and FastAPI experience required.",
        })

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "job_id" in data["data"]


@pytest.mark.asyncio
async def test_optimize_rejects_short_input():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/optimize", json={
            "resume_text": "Short",
            "job_description": "Also short",
        })

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_alignment_score_endpoint() -> None:
    """Test the alignment score endpoint."""
    transport = ASGITransport(app=app)

    # Mock both Embedder and AlignmentScorer to avoid loading the SBERT model
    mock_scorer_result = MagicMock()
    mock_scorer_result.overall_score = 0.75
    mock_scorer_result.gaps = ["python", "docker"]
    mock_scorer_result.section_scores = {"content": 0.75}

    with patch("src.api.routes.optimize.AlignmentScorer") as mock_scorer_cls, \
         patch("src.api.routes.optimize.Embedder") as mock_embedder_cls:
        mock_scorer_cls.return_value.score.return_value = mock_scorer_result
        mock_embedder_cls.return_value = MagicMock()

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/alignment/score",
                json={
                    "resume_text": (
                        "Python developer with 5 years experience "
                        "building REST APIs and PostgreSQL databases."
                    ),
                    "job_description": (
                        "Senior Backend Engineer with Python FastAPI "
                        "PostgreSQL experience required."
                    ),
                },
            )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "overall_score" in data["data"]


@pytest.mark.asyncio
async def test_optimize_endpoint_returns_job_id() -> None:
    """Test that the optimize endpoint returns a job_id (Celery task mocked)."""
    transport = ASGITransport(app=app)

    with patch("src.api.routes.optimize.run_pipeline_task") as mock_task:
        mock_task.apply_async.return_value = MagicMock(id="test-job-id")

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/optimize",
                json={
                    "resume_text": (
                        "Python developer with 5 years experience "
                        "building REST APIs and PostgreSQL databases."
                    ),
                    "job_description": (
                        "Senior Backend Engineer with Python FastAPI "
                        "PostgreSQL experience required."
                    ),
                },
            )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "job_id" in data["data"]


@pytest.mark.asyncio
async def test_optimize_status_endpoint() -> None:
    """Test job status endpoint maps Celery SUCCESS state to 'completed'."""
    transport = ASGITransport(app=app)

    with patch("src.api.routes.optimize.celery_app") as mock_celery:
        mock_result = MagicMock()
        mock_result.state = "SUCCESS"
        mock_celery.AsyncResult.return_value = mock_result

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/optimize/some-job-id/status")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["data"]["job_status"] == "completed"


@pytest.mark.asyncio
async def test_optimize_result_not_ready() -> None:
    """Test result endpoint returns NOT_READY error when the job is still running."""
    transport = ASGITransport(app=app)

    with patch("src.api.routes.optimize.celery_app") as mock_celery:
        mock_result = MagicMock()
        mock_result.state = "STARTED"
        mock_celery.AsyncResult.return_value = mock_result

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/optimize/some-job-id/result")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert data["error"]["code"] == "NOT_READY"
