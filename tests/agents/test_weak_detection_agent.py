"""Tests for WeakDetectionAgent."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from src.agents.base_agent import AgentInput
from src.agents.weak_detection_agent import WeakDetectionAgent


@pytest.fixture
def weak_detection_agent(mock_retriever: AsyncMock, mock_llm: AsyncMock) -> WeakDetectionAgent:
    return WeakDetectionAgent(retriever=mock_retriever, llm_client=mock_llm)


@pytest.mark.asyncio
async def test_weak_detection_finds_keywords_gaps(
    weak_detection_agent: WeakDetectionAgent,
    sample_resume: str,
    sample_jd: str,
) -> None:
    # Arrange
    input_data = AgentInput(content=sample_resume, job_description=sample_jd)

    # Act
    result = await weak_detection_agent.run(input_data)

    # Assert — coverage_gaps must exist and be a list
    assert "coverage_gaps" in result.metadata
    assert isinstance(result.metadata["coverage_gaps"], list)


@pytest.mark.asyncio
async def test_weak_detection_requires_job_description(
    mock_retriever: AsyncMock,
    mock_llm: AsyncMock,
    sample_resume: str,
) -> None:
    # Arrange — empty job_description must be rejected
    agent = WeakDetectionAgent(retriever=mock_retriever, llm_client=mock_llm)
    input_data = AgentInput(content=sample_resume, job_description="")

    # Act & Assert
    with pytest.raises(Exception):
        await agent.run(input_data)


@pytest.mark.asyncio
async def test_weak_detection_score_above_threshold(
    weak_detection_agent: WeakDetectionAgent,
    sample_resume: str,
    sample_jd: str,
) -> None:
    # Arrange
    input_data = AgentInput(content=sample_resume, job_description=sample_jd)

    # Act
    result = await weak_detection_agent.run(input_data)

    # Assert — quality gate requires >= 0.6
    assert result.quality_score >= 0.6


@pytest.mark.asyncio
async def test_weak_detection_identifies_short_bullets(
    weak_detection_agent: WeakDetectionAgent,
    sample_resume: str,
    sample_jd: str,
) -> None:
    # Arrange — resume with obviously short/vague bullets (< 30 chars each)
    short_bullet_resume = sample_resume + "\n- Worked\n- Helped"
    input_data = AgentInput(content=short_bullet_resume, job_description=sample_jd)

    # Act
    result = await weak_detection_agent.run(input_data)

    # Assert — at least one suggestion should flag short or vague bullets
    assert result.suggestions
    assert any(
        "vague" in s.lower() or "short" in s.lower()
        for s in result.suggestions
    )
