"""Tests for Retriever — integration with embedder + vector store."""

import pytest

from src.rag.embedder import Embedder
from src.rag.retriever import Retriever
from src.rag.vector_store import VectorStore


@pytest.fixture
def retriever(tmp_path) -> Retriever:
    embedder = Embedder()
    vector_store = VectorStore(dimension=384, index_dir=str(tmp_path / "indices"))
    return Retriever(embedder, vector_store, user_id="test_user")


@pytest.mark.asyncio
async def test_index_and_retrieve(retriever: Retriever):
    # Arrange
    segments = [
        {"content": "Built REST API with FastAPI serving 10K requests per day", "segment_id": "exp_0"},
        {"content": "Led team of 5 engineers on microservices migration", "segment_id": "exp_1"},
        {"content": "Bachelor of Science in Computer Science from MIT", "segment_id": "edu_0"},
        {"content": "Python, JavaScript, Docker, Kubernetes, AWS", "segment_id": "skills_0"},
    ]

    # Act
    indexed = await retriever.index_segments(segments)
    results = await retriever.retrieve("Python backend API development", top_k=3)

    # Assert
    assert indexed == 4
    assert len(results) == 3
    assert results[0].score > 0  # Has relevance score
    assert results[0].content  # Has content


@pytest.mark.asyncio
async def test_retrieve_empty_index(retriever: Retriever):
    # Act
    results = await retriever.retrieve("anything", top_k=5)

    # Assert
    assert results == []


@pytest.mark.asyncio
async def test_retriever_stats(retriever: Retriever):
    # Arrange
    segments = [{"content": "Test segment", "segment_id": "t0"}]
    await retriever.index_segments(segments)

    # Act
    stats = retriever.get_stats()

    # Assert
    assert stats["indexed_segments"] == 1
    assert stats["total_vectors"] == 1
