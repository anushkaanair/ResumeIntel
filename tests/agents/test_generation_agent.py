"""Tests for GenerationAgent."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.agents.base_agent import AgentInput
from src.agents.generation_agent import GenerationAgent
from src.exceptions import AgentError


def _input(sample_resume: str, sample_jd: str) -> AgentInput:
    return AgentInput(
        content=sample_resume,
        job_description=sample_jd,
        sections={"experience": "Built REST API\nLed migration\nImplemented CI/CD"},
        metadata={"source_text": sample_resume},
    )


@pytest.mark.asyncio
async def test_generation_produces_bullets(mock_retriever, mock_llm, sample_resume, sample_jd) -> None:
    result = await GenerationAgent(mock_retriever, mock_llm).run(_input(sample_resume, sample_jd))
    assert "-" in result.content
    assert result.metadata["grounded"] is True


@pytest.mark.asyncio
async def test_generation_is_rag_grounded(mock_retriever, mock_llm, sample_resume, sample_jd) -> None:
    result = await GenerationAgent(mock_retriever, mock_llm).run(_input(sample_resume, sample_jd))
    assert result.sources


@pytest.mark.asyncio
async def test_generation_rejects_empty_content(mock_retriever, mock_llm, sample_jd) -> None:
    with pytest.raises(Exception):
        await GenerationAgent(mock_retriever, mock_llm).run(AgentInput(content="", job_description=sample_jd))


@pytest.mark.asyncio
async def test_generation_quality_score_above_threshold(mock_retriever, mock_llm, sample_resume, sample_jd) -> None:
    result = await GenerationAgent(mock_retriever, mock_llm).run(_input(sample_resume, sample_jd))
    assert result.quality_score >= 0.7


@pytest.mark.asyncio
async def test_generation_refuses_invented_numbers_and_skills(
    mock_retriever, fabricating_llm: AsyncMock, sample_resume, sample_jd
) -> None:
    """A rewrite adding 3x / 40% / Kubernetes must fail the gate, not pass it."""
    with pytest.raises(AgentError) as exc:
        await GenerationAgent(mock_retriever, fabricating_llm).run(_input(sample_resume, sample_jd))
    assert "absent from the source" in exc.value.context["last_error"]
    assert fabricating_llm.generate.await_count == 3  # retried, with feedback, then gave up


@pytest.mark.asyncio
async def test_generation_feedback_names_the_offending_numbers(
    mock_retriever, fabricating_llm: AsyncMock, sample_resume, sample_jd
) -> None:
    with pytest.raises(AgentError):
        await GenerationAgent(mock_retriever, fabricating_llm).run(_input(sample_resume, sample_jd))
    second_prompt = fabricating_llm.generate.await_args_list[1].args[0]
    assert "REJECTED" in second_prompt and "40" in second_prompt  # names the offending number
