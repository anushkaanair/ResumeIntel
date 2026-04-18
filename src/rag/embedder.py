"""SBERT Embedder — Encodes text segments into dense vectors for FAISS.

Supports two model tiers:
  - English-only (default): all-MiniLM-L6-v2 (384-dim, fast)
  - Multilingual: paraphrase-multilingual-MiniLM-L12-v2 (384-dim, 50+ languages)

Language detection via langdetect triggers automatic multilingual model selection
when the detected language is not English.
"""

from __future__ import annotations

import numpy as np
import structlog
from sentence_transformers import SentenceTransformer

logger = structlog.get_logger()

ENGLISH_MODEL      = "all-MiniLM-L6-v2"
MULTILINGUAL_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIM      = 384


def _detect_language(text: str) -> str:
    """Return ISO 639-1 language code for the given text, defaulting to 'en'."""
    try:
        from langdetect import detect  # type: ignore[import]
        return detect(text[:500])
    except Exception:
        return "en"


class Embedder:
    """Encodes text into normalized embeddings using Sentence-BERT.

    Pass multilingual=True (or let auto_detect=True infer it from text) to
    switch to the multilingual model for non-English resumes.
    """

    def __init__(
        self,
        model_name: str = ENGLISH_MODEL,
        multilingual: bool = False,
        auto_detect: bool = False,
        sample_text: str = "",
    ) -> None:
        if auto_detect and sample_text:
            lang = _detect_language(sample_text)
            if lang != "en":
                multilingual = True
                logger.info("embedder.language_detected", lang=lang, switching_to="multilingual")

        if multilingual:
            model_name = MULTILINGUAL_MODEL

        logger.info("embedder.loading", model=model_name)
        self.model = SentenceTransformer(model_name)
        self.dimension = EMBEDDING_DIM
        self.is_multilingual = multilingual

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
