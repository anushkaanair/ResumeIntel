"""Tests for API routes."""

import pytest
from httpx import ASGITransport, AsyncClient

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
