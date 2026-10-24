"""Tests for VectorStore."""

import numpy as np
import pytest

from src.rag.vector_store import VectorStore


@pytest.fixture
def vector_store(tmp_path) -> VectorStore:
    return VectorStore(dimension=384, index_dir=str(tmp_path / "indices"))


def test_create_index(vector_store: VectorStore):
    # Act
    index = vector_store.get_or_create_index("user1")

    # Assert
    assert index.ntotal == 0


def test_add_and_search(vector_store: VectorStore):
    # Arrange
    vectors = np.random.randn(5, 384).astype(np.float32)
    # Normalize for inner product search
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    vectors = vectors / norms

    metadata = [{"content": f"segment_{i}", "segment_id": f"s{i}"} for i in range(5)]

    # Act
    vector_store.add_vectors("user1", vectors, metadata)
    query = vectors[0:1]  # Search for first vector
    results = vector_store.search("user1", query, top_k=3)

    # Assert
    assert len(results) == 3
    assert results[0][0] > 0.9  # First result should be very similar (same vector)
    assert results[0][2]["segment_id"] == "s0"


def test_user_isolation(vector_store: VectorStore):
    # Arrange
    v1 = np.random.randn(3, 384).astype(np.float32)
    v2 = np.random.randn(2, 384).astype(np.float32)

    vector_store.add_vectors("user1", v1, [{"id": i} for i in range(3)])
    vector_store.add_vectors("user2", v2, [{"id": i} for i in range(2)])

    # Assert — indices are isolated
    stats1 = vector_store.get_stats("user1")
    stats2 = vector_store.get_stats("user2")
    assert stats1["total_vectors"] == 3
    assert stats2["total_vectors"] == 2


def test_save_and_load(vector_store: VectorStore):
    # Arrange
    vectors = np.random.randn(3, 384).astype(np.float32)
    metadata = [{"content": f"seg_{i}"} for i in range(3)]
    vector_store.add_vectors("user1", vectors, metadata)

    # Act
    vector_store.save_index("user1")
    # Remove from memory and reload
    del vector_store.indices["user1"]
    index = vector_store.get_or_create_index("user1")

    # Assert
    assert index.ntotal == 3


def test_add_vectors_dedupes_by_segment_id_and_persists_metadata(tmp_path) -> None:
    import numpy as np

    from src.rag.vector_store import VectorStore

    vs = VectorStore(index_dir=str(tmp_path))
    vecs = np.random.rand(2, 384).astype("float32")
    meta = [{"segment_id": "a", "content": "x"}, {"segment_id": "b", "content": "y"}]
    assert vs.add_vectors("u", vecs, meta) == 2
    assert vs.add_vectors("u", vecs, meta) == 0  # a retry must not duplicate the index
    vs.save_index("u")

    again = VectorStore(index_dir=str(tmp_path))
    again.get_or_create_index("u")
    assert again.get_stats("u")["total_vectors"] == 2
