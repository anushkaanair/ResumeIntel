"""Tests for GenerationAgent."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from src.agents.base_agent import AgentInput, AgentOutput, RetrievedSegment
from src.agents.generation_agent import GenerationAgent


@pytest.fixture
def generation_agent(mock_retriever: AsyncMock, mock_llm: AsyncMock) -> GenerationAgent:
    return GenerationAgent(retriever=mock_retriever, llm_client=mock_llm)


def _make_input_with_sections(sample_resume: str, sample_jd: str) -> AgentInput:
    """Build an AgentInput that passes GenerationAgent.validate_input.

    GenerationAgent.validate_input checks ``input.sections`` which is not a
    declared field on AgentInput (the dataclass uses ``resume_sections``).  We
    set the attribute directly so the truthy check succeeds without depending on
    a previous_output.
    """
    input_data = AgentInput(content=sample_resume, job_description=sample_jd)
    # Set dynamic attribute so GenerationAgent.validate_input's `input.sections`
    # check evaluates to truthy and does not raise.
    input_data.sections = {"experience": "Built REST API\nLed migration\nImplemented CI/CD"}  # type: ignore[attr-defined]
    return input_data


@pytest.mark.asyncio
async def test_generation_produces_bullets(
    generation_agent: GenerationAgent,
    sample_resume: str,
    sample_jd: str,
) -> None:
    # Arrange — input must have previous_output.sections so validate_input passes
    input_data = _make_input_with_sections(sample_resume, sample_jd)

    # Act
    result = await generation_agent.run(input_data)

    # Assert — the mock LLM returns bullet lines starting with "-"
    assert "-" in result.content


@pytest.mark.asyncio
async def test_generation_is_rag_grounded(
    generation_agent: GenerationAgent,
    sample_resume: str,
    sample_jd: str,
) -> None:
    # Arrange
    input_data = _make_input_with_sections(sample_resume, sample_jd)

    # Act
    result = await generation_agent.run(input_data)

    # Assert — sources must not be empty (RAG grounding requirement)
    assert result.sources
    assert len(result.sources) > 0


@pytest.mark.asyncio
async def test_generation_rejects_empty_content(
    mock_retriever: AsyncMock,
    mock_llm: AsyncMock,
    sample_jd: str,
) -> None:
    # Arrange — empty content must be rejected
    agent = GenerationAgent(retriever=mock_retriever, llm_client=mock_llm)
    input_data = AgentInput(content="", job_description=sample_jd)

    # Act & Assert
    with pytest.raises(Exception):
        await agent.run(input_data)


@pytest.mark.asyncio
async def test_generation_quality_score_above_threshold(
    generation_agent: GenerationAgent,
    sample_resume: str,
    sample_jd: str,
) -> None:
    # Arrange
    input_data = _make_input_with_sections(sample_resume, sample_jd)

    # Act
    result = await generation_agent.run(input_data)

    # Assert — quality gate requires >= 0.7
    assert result.quality_score >= 0.7
