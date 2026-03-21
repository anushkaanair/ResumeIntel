"""Tests for InterviewAgent."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from src.agents.base_agent import AgentInput
from src.agents.interview_agent import InterviewAgent


@pytest.fixture
def comprehensive_interview_llm() -> AsyncMock:
    """LLM that returns full interview prep covering all four scored sections."""
    llm = AsyncMock()
    llm.generate.return_value = """
## Behavioral Questions
1. Tell me about a time you led a project.
STAR Framework: Situation — led REST API migration; Task — reduce latency by 30%;
Action — designed microservices split; Result — 3x scalability improvement.

## Technical Questions
1. Explain your PostgreSQL optimization experience.
2. How did you implement the CI/CD pipeline that cut deployment time by 60%?

## Talking Points
- REST API with 99.9% uptime serving 10,000+ daily requests
- Microservices migration improved scalability by 3x
- CI/CD pipeline reduced deployment time by 60%

## Questions to Ask
1. What are the biggest technical challenges the team faces today?
2. How does the team approach architectural decisions?
"""
    return llm


@pytest.fixture
def interview_agent(mock_retriever: AsyncMock, mock_llm: AsyncMock) -> InterviewAgent:
    return InterviewAgent(retriever=mock_retriever, llm_client=mock_llm)


@pytest.fixture
def interview_agent_comprehensive(
    mock_retriever: AsyncMock,
    comprehensive_interview_llm: AsyncMock,
) -> InterviewAgent:
    return InterviewAgent(retriever=mock_retriever, llm_client=comprehensive_interview_llm)


@pytest.mark.asyncio
async def test_interview_generates_questions(
    interview_agent_comprehensive: InterviewAgent,
    sample_resume: str,
    sample_jd: str,
) -> None:
    # Arrange
    input_data = AgentInput(content=sample_resume, job_description=sample_jd)

    # Act
    result = await interview_agent_comprehensive.run(input_data)

    # Assert — prep material must be non-empty
    assert isinstance(result.content, str)
    assert len(result.content.strip()) > 0


@pytest.mark.asyncio
async def test_interview_requires_resume_content(
    mock_retriever: AsyncMock,
    mock_llm: AsyncMock,
    sample_jd: str,
) -> None:
    # Arrange — empty content must be rejected
    agent = InterviewAgent(retriever=mock_retriever, llm_client=mock_llm)
    input_data = AgentInput(content="", job_description=sample_jd)

    # Act & Assert
    with pytest.raises(Exception):
        await agent.run(input_data)


@pytest.mark.asyncio
async def test_interview_score_reflects_completeness(
    interview_agent_comprehensive: InterviewAgent,
    sample_resume: str,
    sample_jd: str,
) -> None:
    # Arrange — comprehensive_interview_llm returns content with "Behavioral",
    # "Technical", "Talking Points", and "Questions to Ask", which maximises
    # _score_prep (0.4 base + 0.15 * 4 sections = 1.0, capped at 1.0).
    input_data = AgentInput(content=sample_resume, job_description=sample_jd)

    # Act
    result = await interview_agent_comprehensive.run(input_data)

    # Assert — all four sections present → score should be >= 0.85
    assert result.quality_score >= 0.85
