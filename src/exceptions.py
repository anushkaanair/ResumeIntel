from __future__ import annotations

from typing import Any


class ResumeIntelError(Exception):
    """Base exception for the resume-intel platform."""

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        self.message = message
        self.context = context or {}
        super().__init__(self.message)


class AgentError(ResumeIntelError):
    """Raised when an AI agent encounters an error during processing."""


class RAGError(ResumeIntelError):
    """Raised when retrieval-augmented generation fails."""


class ParsingError(ResumeIntelError):
    """Raised when resume or document parsing fails."""


class QualityGateError(ResumeIntelError):
    """Raised when a quality gate check does not pass."""


class ValidationError(ResumeIntelError):
    """Raised when input validation fails."""
