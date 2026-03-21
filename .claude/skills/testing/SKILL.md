---
name: testing
description: Write tests for the resume intelligence system using pytest and pytest-asyncio. Use when creating unit tests, integration tests, or test fixtures for agents, RAG, API, or scoring modules. Triggers on "write test", "add test", "test for", "testing", "pytest".
---

# Testing Patterns

## Agent Test
```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.agents.quality_agent import QualityAgent

@pytest.fixture
def mock_retriever():
    retriever = AsyncMock()
    retriever.retrieve.return_value = [
        RetrievedSegment(content="Built REST API with 99.9% uptime", score=0.89)
    ]
    return retriever

@pytest.fixture
def quality_agent(mock_retriever):
    return QualityAgent(retriever=mock_retriever, llm_client=AsyncMock())

@pytest.mark.asyncio
async def test_quality_agent_strengthens_weak_bullet(quality_agent):
    # Arrange
    input = AgentInput(content="Worked on API")

    # Act
    result = await quality_agent.execute(input)

    # Assert
    assert result.quality_score >= 0.7
    assert any(char.isdigit() for char in result.content)
```

## API Test
```python
from httpx import AsyncClient, ASGITransport
from src.api import app

@pytest.mark.asyncio
async def test_optimize_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/optimize", json={
            "resume_text": "5 years Python experience...",
            "job_description": "Senior Backend Engineer..."
        })
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

## Rules
- AAA pattern: Arrange, Act, Assert
- Mock external dependencies (LLM, DB), never real calls in unit tests
- One assertion concept per test
- Fixtures in conftest.py for shared setup
- Test file mirrors source: src/agents/quality_agent.py -> tests/agents/test_quality_agent.py
