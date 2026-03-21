"""LLM client wrapper around the OpenAI SDK."""
from __future__ import annotations

import structlog
from openai import AsyncOpenAI

from src.config.settings import settings

logger = structlog.get_logger()


class LLMClient:
    """Async wrapper around OpenAI chat completions.

    Agents call ``await self.llm.generate(prompt)`` to obtain a text response.
    """

    def __init__(self, model: str | None = None) -> None:
        if settings.llm_provider == "ollama":
            self.client = AsyncOpenAI(
                base_url=settings.ollama_base_url,
                api_key="ollama",  # required by SDK but ignored by Ollama
            )
            self.model = model or settings.ollama_model
        else:
            self.client = AsyncOpenAI(api_key=settings.openai_api_key)
            self.model = model or "gpt-4o"

    _SYSTEM_PROMPT = (
        "You are Resume Intel, an AI assistant specializing in resume optimization, "
        "ATS alignment, and career coaching. You produce structured, professional output "
        "grounded only in the source data provided. You never fabricate achievements, "
        "metrics, skills, or experiences. When in doubt, be conservative and honest."
    )

    async def generate(self, prompt: str, temperature: float = 0.3, max_tokens: int = 4096) -> str:
        """Generate text completion from prompt.

        Args:
            prompt: The user prompt to send to the model.
            temperature: Sampling temperature (0.0–1.0). Lower = more deterministic.
            max_tokens: Maximum tokens in the response.

        Returns:
            The model's text response.
        """
        logger.info("llm.generate", model=self.model, prompt_len=len(prompt))
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self._SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content or ""
        logger.info("llm.response", model=self.model, response_len=len(content))
        return content
