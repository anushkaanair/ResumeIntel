"""Base agent class for the resume optimization pipeline."""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any

import structlog

from src.exceptions import AgentError, QualityGateError

logger = structlog.get_logger()


@dataclass
class RetrievedSegment:
    """A segment retrieved from the RAG vector store."""

    content: str
    score: float
    segment_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentInput:
    """Standard input for all agents in the pipeline."""

    content: str
    resume_sections: dict[str, str] = field(default_factory=dict)
    job_description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    previous_output: AgentOutput | None = None


@dataclass
class AgentOutput:
    """Standard output for all agents in the pipeline."""

    content: str
    quality_score: float = 0.0
    sources: list[RetrievedSegment] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    sections: dict[str, str] = field(default_factory=dict)
    suggestions: list[str] = field(default_factory=list)


class BaseAgent(abc.ABC):
    """Abstract base class for all pipeline agents.

    Every agent must:
    1. Inherit from BaseAgent
    2. Implement execute(), validate_input(), validate_output()
    3. Define QUALITY_THRESHOLD and MAX_RETRIES
    4. Use RAG retrieval before any generation
    """

    QUALITY_THRESHOLD: float = 0.7
    MAX_RETRIES: int = 3

    @abc.abstractmethod
    async def execute(self, input: AgentInput) -> AgentOutput:
        """Run the agent's core logic."""
        ...

    @abc.abstractmethod
    def validate_input(self, input: AgentInput) -> None:
        """Validate input before processing. Raise ValueError if invalid."""
        ...

    @abc.abstractmethod
    def validate_output(self, output: AgentOutput) -> None:
        """Validate output quality. Raise QualityGateError if below threshold."""
        ...

    async def run(self, input: AgentInput) -> AgentOutput:
        """Execute with retry logic and quality gate enforcement."""
        agent_name = self.__class__.__name__
        logger.info("agent.start", agent=agent_name)

        last_error: Exception | None = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                self.validate_input(input)
                output = await self.execute(input)
                self.validate_output(output)

                logger.info(
                    "agent.complete",
                    agent=agent_name,
                    attempt=attempt,
                    quality_score=output.quality_score,
                )
                return output

            except QualityGateError as e:
                last_error = e
                logger.warning(
                    "agent.quality_gate_failed",
                    agent=agent_name,
                    attempt=attempt,
                    error=str(e),
                )
            except Exception as e:
                last_error = e
                logger.error(
                    "agent.error",
                    agent=agent_name,
                    attempt=attempt,
                    error=str(e),
                )

        raise AgentError(
            f"{agent_name} failed after {self.MAX_RETRIES} attempts",
            context={"last_error": str(last_error)},
        )
