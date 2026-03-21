"""FastAPI dependency injection helpers."""
from __future__ import annotations

from src.llm.client import LLMClient

_llm_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Return a module-level singleton LLMClient instance."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
