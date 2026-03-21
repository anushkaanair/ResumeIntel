"""Tests for QualityAgent."""

import pytest
from unittest.mock import AsyncMock

from src.agents.base_agent import AgentInput
from src.agents.quality_agent import QualityAgent


@pytest.fixture
def quality_agent(mock_retriever: AsyncMock, mock_llm: AsyncMock) -> QualityAgent:
    return QualityAgent(retriever=mock_retriever, llm_client=mock_llm)


@pytest.mark.asyncio
async def test_quality_agent_scores_output(quality_agent: QualityAgent):
    # Arrange
    content = (
        "- Led development of REST API serving 10K requests/day\n"
        "- Implemented CI/CD pipeline reducing deployment time by 60%\n"
        "- Designed microservices architecture handling 1M daily events"
    )
    input_data = AgentInput(content=content)

    # Act
    result = await quality_agent.run(input_data)

    # Assert
    assert result.quality_score >= 0.7


@pytest.mark.asyncio
async def test_quality_agent_detects_weak_bullets(quality_agent: QualityAgent):
    # Arrange — content with weak verbs and no metrics
    content = (
        "- Worked on the API project\n"
        "- Helped with database tasks\n"
        "- Assisted team with deployment"
    )
    input_data = AgentInput(content=content)

    # Act
    result = await quality_agent.run(input_data)

    # Assert
    assert result.metadata.get("improved") is True or result.suggestions
