"""Retriever — Orchestrates embedding + vector search for RAG pipeline."""

from __future__ import annotations

from typing import Any

import structlog

from src.agents.base_agent import RetrievedSegment
from src.rag.embedder import Embedder
from src.rag.vector_store import VectorStore

logger = structlog.get_logger()


class Retriever:
    """High-level retrieval interface combining embedder and vector store.

    Usage:
        retriever = Retriever(embedder, vector_store, user_id="user123")
        await retriever.index_segments(segments)
        results = await retriever.retrieve("Python backend developer", top_k=5)
    """

    def __init__(
        self,
        embedder: Embedder,
        vector_store: VectorStore,
        user_id: str = "default",
    ) -> None:
        self.embedder = embedder
        self.vector_store = vector_store
        self.user_id = user_id
        self._segments: list[dict[str, Any]] = []

    async def index_segments(self, segments: list[dict[str, Any]]) -> int:
        """Embed and index a list of segments.

        Args:
            segments: List of dicts with at least 'content' and 'segment_id' keys.

        Returns:
            Number of segments indexed.
        """
        if not segments:
            return 0

        texts = [seg["content"] for seg in segments]
        vectors = self.embedder.encode(texts)

        metadata = [
            {
                "content": seg["content"],
                "segment_id": seg.get("segment_id", f"seg_{i}"),
                "section": seg.get("section", "unknown"),
                "index": seg.get("index", i),
            }
            for i, seg in enumerate(segments)
        ]

        self._segments.extend(metadata)
        count = self.vector_store.add_vectors(self.user_id, vectors, metadata)

        logger.info("retriever.indexed", user_id=self.user_id, count=count)
        return count

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[RetrievedSegment]:
        """Retrieve the most relevant segments for a query.

        Args:
            query: Natural language query to search for.
            top_k: Number of results to return.

        Returns:
            List of RetrievedSegment with content, score, and metadata.
        """
        query_vector = self.embedder.encode([query])
        results = self.vector_store.search(self.user_id, query_vector, top_k)

        retrieved = []
        for score, idx, meta in results:
            retrieved.append(
                RetrievedSegment(
                    content=meta.get("content", ""),
                    score=score,
                    segment_id=meta.get("segment_id", ""),
                    metadata=meta,
                )
            )

        logger.info(
            "retriever.retrieved",
            user_id=self.user_id,
            query_len=len(query),
            results=len(retrieved),
            top_score=retrieved[0].score if retrieved else 0.0,
        )
        return retrieved

    async def retrieve_by_section(
        self,
        query: str,
        section: str,
        top_k: int = 5,
    ) -> list[RetrievedSegment]:
        """Retrieve segments filtered by section name."""
        all_results = await self.retrieve(query, top_k=top_k * 3)
        filtered = [r for r in all_results if r.metadata.get("section") == section]
        return filtered[:top_k]

    def get_stats(self) -> dict[str, Any]:
        """Get retriever statistics."""
        return {
            "user_id": self.user_id,
            "indexed_segments": len(self._segments),
            **self.vector_store.get_stats(self.user_id),
        }
