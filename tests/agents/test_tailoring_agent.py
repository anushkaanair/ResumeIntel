"""Tests for TailoringAgent."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from src.agents.base_agent import AgentInput
from src.agents.tailoring_agent import TailoringAgent


# LLM output that contains many keywords from the sample JD so _calculate_alignment
# returns a score >= 0.7 (keywords like python, fastapi, postgresql, docker, aws,
# backend, scalable, services, restful, apis, optimize, database, performance, etc.)
JD_RICH_RESPONSE = (
    "Senior Backend Engineer profile with Python FastAPI Django PostgreSQL Docker AWS "
    "experience. Design implement scalable backend services RESTful APIs optimize database "
    "performance queries lead technical projects mentor junior engineers cloud platforms "
    "problem solving skills development experience knowledge."
)


@pytest.fixture
def jd_rich_llm() -> AsyncMock:
    llm = AsyncMock()
    llm.generate.return_value = JD_RICH_RESPONSE
    return llm


@pytest.fixture
def tailoring_agent(mock_retriever: AsyncMock, mock_llm: AsyncMock) -> TailoringAgent:
    return TailoringAgent(retriever=mock_retriever, llm_client=mock_llm)


@pytest.fixture
def tailoring_agent_passing(mock_retriever: AsyncMock, jd_rich_llm: AsyncMock) -> TailoringAgent:
    """TailoringAgent wired with a JD-keyword-rich LLM response to clear the 0.7 gate."""
    return TailoringAgent(retriever=mock_retriever, llm_client=jd_rich_llm)


@pytest.mark.asyncio
async def test_tailoring_returns_content(
    tailoring_agent_passing: TailoringAgent,
    sample_resume: str,
    sample_jd: str,
) -> None:
    # Arrange
    input_data = AgentInput(content=sample_resume, job_description=sample_jd)

    # Act
    result = await tailoring_agent_passing.run(input_data)

    # Assert — tailored content must be a non-empty string
    assert isinstance(result.content, str)
    assert len(result.content.strip()) > 0


@pytest.mark.asyncio
async def test_tailoring_requires_job_description(
    mock_retriever: AsyncMock,
    mock_llm: AsyncMock,
    sample_resume: str,
) -> None:
    # Arrange — empty job_description must be rejected
    agent = TailoringAgent(retriever=mock_retriever, llm_client=mock_llm)
    input_data = AgentInput(content=sample_resume, job_description="")

    # Act & Assert
    with pytest.raises(Exception):
        await agent.run(input_data)


@pytest.mark.asyncio
async def test_tailoring_score_above_threshold(
    tailoring_agent_passing: TailoringAgent,
    sample_resume: str,
    sample_jd: str,
) -> None:
    # Arrange — using jd_rich_llm which returns content dense with JD keywords,
    # ensuring _calculate_alignment returns >= 0.7 and the quality gate passes.
    input_data = AgentInput(content=sample_resume, job_description=sample_jd)

    # Act
    result = await tailoring_agent_passing.run(input_data)

    # Assert
    assert result.quality_score >= 0.7
