"""Tests for IngestionAgent."""

import pytest
from unittest.mock import AsyncMock

from src.agents.base_agent import AgentInput
from src.agents.ingestion_agent import IngestionAgent


@pytest.fixture
def ingestion_agent(mock_retriever: AsyncMock) -> IngestionAgent:
    return IngestionAgent(retriever=mock_retriever)


@pytest.mark.asyncio
async def test_ingestion_extracts_sections(ingestion_agent: IngestionAgent, sample_resume: str):
    # Arrange
    input_data = AgentInput(content=sample_resume)

    # Act
    result = await ingestion_agent.run(input_data)

    # Assert
    assert result.sections
    assert "experience" in result.sections or "work experience" in result.sections


@pytest.mark.asyncio
async def test_ingestion_indexes_segments(ingestion_agent: IngestionAgent, sample_resume: str):
    # Arrange
    input_data = AgentInput(content=sample_resume)

    # Act
    result = await ingestion_agent.run(input_data)

    # Assert
    assert result.metadata["segment_count"] > 0
    ingestion_agent.retriever.index_segments.assert_called_once()


@pytest.mark.asyncio
async def test_ingestion_rejects_short_input(ingestion_agent: IngestionAgent):
    # Arrange
    input_data = AgentInput(content="Too short")

    # Act & Assert
    with pytest.raises(Exception):
        await ingestion_agent.run(input_data)
