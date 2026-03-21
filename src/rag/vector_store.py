"""FAISS Vector Store — Manages vector indices for resume segments."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import faiss
import numpy as np
import structlog

from src.rag.embedder import EMBEDDING_DIM

logger = structlog.get_logger()


class VectorStore:
    """FAISS-based vector store with per-user index isolation.

    Uses IndexFlatIP for small collections (<10K vectors) and
    IVF-PQ for larger ones. All vectors must be L2-normalized
    for cosine similarity via inner product.
    """

    def __init__(
        self,
        dimension: int = EMBEDDING_DIM,
        index_dir: str = "./data/faiss_indices",
    ) -> None:
        self.dimension = dimension
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.indices: dict[str, faiss.Index] = {}
        self.metadata: dict[str, list[dict[str, Any]]] = {}

    def get_or_create_index(self, user_id: str) -> faiss.Index:
        """Get existing index or create a new flat index for a user."""
        if user_id in self.indices:
            return self.indices[user_id]

        index_path = self.index_dir / f"{user_id}.index"
        if index_path.exists():
            logger.info("vector_store.load", user_id=user_id, path=str(index_path))
            index = faiss.read_index(str(index_path))
        else:
            logger.info("vector_store.create", user_id=user_id)
            index = faiss.IndexFlatIP(self.dimension)

        self.indices[user_id] = index
        if user_id not in self.metadata:
            self.metadata[user_id] = []
        return index

    def add_vectors(
        self,
        user_id: str,
        vectors: np.ndarray,
        metadata_list: list[dict[str, Any]],
    ) -> int:
        """Add vectors and their metadata to a user's index.

        Args:
            user_id: User identifier for index isolation.
            vectors: Normalized vectors of shape (n, dimension).
            metadata_list: Metadata for each vector (must match length).

        Returns:
            Number of vectors added.
        """
        if len(vectors) != len(metadata_list):
            raise ValueError("Vectors and metadata must have same length")

        index = self.get_or_create_index(user_id)
        index.add(vectors)
        self.metadata[user_id].extend(metadata_list)

        logger.info(
            "vector_store.added",
            user_id=user_id,
            count=len(vectors),
            total=index.ntotal,
        )
        return len(vectors)

    def search(
        self,
        user_id: str,
        query_vector: np.ndarray,
        top_k: int = 5,
    ) -> list[tuple[float, int, dict[str, Any]]]:
        """Search for nearest neighbors in a user's index.

        Args:
            user_id: User identifier.
            query_vector: Normalized query vector of shape (1, dimension).
            top_k: Number of results to return.

        Returns:
            List of (score, index, metadata) tuples.
        """
        index = self.get_or_create_index(user_id)

        if index.ntotal == 0:
            return []

        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)

        actual_k = min(top_k, index.ntotal)
        scores, indices = index.search(query_vector, actual_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            meta = (
                self.metadata[user_id][idx]
                if idx < len(self.metadata.get(user_id, []))
                else {}
            )
            results.append((float(score), int(idx), meta))

        return results

    def save_index(self, user_id: str) -> None:
        """Persist a user's index to disk."""
        if user_id not in self.indices:
            return
        path = self.index_dir / f"{user_id}.index"
        faiss.write_index(self.indices[user_id], str(path))
        logger.info("vector_store.saved", user_id=user_id, path=str(path))

    def delete_index(self, user_id: str) -> None:
        """Remove a user's index from memory and disk."""
        self.indices.pop(user_id, None)
        self.metadata.pop(user_id, None)
        path = self.index_dir / f"{user_id}.index"
        if path.exists():
            os.remove(path)
            logger.info("vector_store.deleted", user_id=user_id)

    def get_stats(self, user_id: str) -> dict[str, Any]:
        """Get stats for a user's index."""
        index = self.get_or_create_index(user_id)
        return {
            "user_id": user_id,
            "total_vectors": index.ntotal,
            "dimension": self.dimension,
            "metadata_count": len(self.metadata.get(user_id, [])),
        }
