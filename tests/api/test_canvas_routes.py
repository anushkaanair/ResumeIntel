"""Tests for Canvas API mock routes."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.api import app

@pytest.mark.asyncio
async def test_reoptimize_section():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/canvas/section/sec-123/reoptimize", json={
            "section_id": "sec-123",
            "section_title": "Experience"
        })

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["data"]["section_id"] == "sec-123"
    assert "re-optimized by AI" in data["data"]["message"]

@pytest.mark.asyncio
async def test_enhance_section():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/canvas/section/sec-123/enhance", json={
            "section_id": "sec-123",
            "section_title": "Experience",
            "prompt": "Make it sound more leadership-focused"
        })

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["data"]["section_id"] == "sec-123"
    assert "leadership-focused" in data["data"]["message"]

@pytest.mark.asyncio
async def test_refresh_linkedin():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/canvas/profile/linkedin/refresh")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "has_changes" in data["data"]
    assert "items" in data["data"]
    assert isinstance(data["data"]["items"], list)

@pytest.mark.asyncio
async def test_refresh_github():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/canvas/profile/github/refresh")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "has_changes" in data["data"]
    assert "items" in data["data"]
    assert isinstance(data["data"]["items"], list)
