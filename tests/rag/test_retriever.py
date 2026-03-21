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


def test_retriever_initialization():
    """Test Retriever can be initialized with correct attributes."""
    from unittest.mock import MagicMock

    # Arrange
    mock_embedder = MagicMock()
    mock_vector_store = MagicMock()

    # Act
    retriever_instance = Retriever(
        embedder=mock_embedder,
        vector_store=mock_vector_store,
        user_id="user123",
    )

    # Assert
    assert retriever_instance.user_id == "user123"
    assert retriever_instance.embedder is mock_embedder
    assert retriever_instance.vector_store is mock_vector_store


@pytest.mark.asyncio
async def test_retriever_index_segments_returns_count():
    """Test that indexing segments returns the correct count without real model."""
    import numpy as np
    from unittest.mock import MagicMock, patch
    from src.rag.embedder import Embedder
    from src.rag.vector_store import VectorStore

    # Arrange — patch encode so no SBERT model is loaded
    segments = [
        {"content": "Built REST API with FastAPI", "segment_id": "exp_0"},
        {"content": "Led microservices migration", "segment_id": "exp_1"},
        {"content": "Python, Docker, AWS skills", "segment_id": "skills_0"},
    ]

    with patch.object(
        Embedder,
        "encode",
        return_value=np.random.rand(len(segments), 384).astype("float32"),
    ):
        mock_embedder = Embedder.__new__(Embedder)
        mock_vector_store = MagicMock()
        mock_vector_store.add.return_value = None

        retriever_instance = Retriever(
            embedder=mock_embedder,
            vector_store=mock_vector_store,
            user_id="test_user",
        )

        # Act
        count = await retriever_instance.index_segments(segments)

    # Assert
    assert count == len(segments)
