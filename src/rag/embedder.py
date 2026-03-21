"""SBERT Embedder — Encodes text segments into dense vectors for FAISS."""

from __future__ import annotations

import numpy as np
import structlog
from sentence_transformers import SentenceTransformer

logger = structlog.get_logger()

# Default model: 384-dim, fast, good for semantic similarity
DEFAULT_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


class Embedder:
    """Encodes text into normalized embeddings using Sentence-BERT."""

    def __init__(self, model_name: str = DEFAULT_MODEL) -> None:
        logger.info("embedder.loading", model=model_name)
        self.model = SentenceTransformer(model_name)
        self.dimension = EMBEDDING_DIM

    def encode(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        """Encode a list of texts into normalized embedding vectors.

        Args:
            texts: List of text strings to encode.
            batch_size: Batch size for encoding.

        Returns:
            np.ndarray of shape (len(texts), dimension), L2-normalized.
        """
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)

        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,  # Critical for cosine similarity via inner product
            show_progress_bar=False,
        )

        logger.info("embedder.encoded", count=len(texts), dim=embeddings.shape[1])
        return embeddings.astype(np.float32)

    def encode_single(self, text: str) -> np.ndarray:
        """Encode a single text string."""
        return self.encode([text])[0]
