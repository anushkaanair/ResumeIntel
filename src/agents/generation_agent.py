"""Generation Agent — Generates optimized resume bullets using RAG-grounded LLM."""

from __future__ import annotations

import structlog

from src.agents.base_agent import AgentInput, AgentOutput, BaseAgent
from src.exceptions import QualityGateError
from src.rag.retriever import Retriever

logger = structlog.get_logger()


class GenerationAgent(BaseAgent):
    """Generates optimized, ATS-friendly resume bullets grounded in source data."""

    QUALITY_THRESHOLD = 0.7
    MAX_RETRIES = 3

    def __init__(self, retriever: Retriever, llm_client: object) -> None:
        self.retriever = retriever
        self.llm = llm_client

    async def execute(self, input: AgentInput) -> AgentOutput:
        self.validate_input(input)

        # RAG: retrieve relevant context from indexed resume segments
        context = await self.retriever.retrieve(
            query=input.job_description or input.content,
            top_k=10,
        )

        prompt = self._build_prompt(input, context)
        result = await self.llm.generate(prompt)

        output = AgentOutput(
            content=result,
            quality_score=self._score_output(result, context),
            sources=context,
            metadata={"grounded": True, "source_count": len(context)},
        )
        self.validate_output(output)
        return output

    def validate_input(self, input: AgentInput) -> None:
        if not input.content:
            raise ValueError("Empty resume content")
        if not input.sections and not input.previous_output:
            raise ValueError("No parsed sections available — run IngestionAgent first")

    def validate_output(self, output: AgentOutput) -> None:
        if output.quality_score < self.QUALITY_THRESHOLD:
            raise QualityGateError(
                f"Generation quality {output.quality_score:.2f} below threshold"
            )
        if not output.sources:
            raise QualityGateError("Output not grounded in any source data")

    def _build_prompt(self, input: AgentInput, context: list) -> str:
        context_text = "\n".join(
            f"- {seg.content} (relevance: {seg.score:.2f})" for seg in context
        )

        sections = input.sections or (
            input.previous_output.sections if input.previous_output else {}
        )
        sections_text = "\n".join(
            f"### {name}\n{content}" for name, content in sections.items()
        )

        return f"""You are an expert resume optimizer. Generate ATS-optimized resume bullets.

RULES:
- Every bullet MUST be grounded in the source data below — no fabricated achievements
- Use strong action verbs (Led, Designed, Implemented, Optimized, Delivered)
- Include quantifiable metrics where available in source
- Target keywords from the job description
- Keep bullets concise (1-2 lines each)

SOURCE RESUME DATA:
{sections_text}

RELEVANT CONTEXT (from RAG retrieval):
{context_text}

TARGET JOB DESCRIPTION:
{input.job_description or "General optimization — improve impact and clarity"}

Generate optimized resume bullets for each section. Format as markdown sections."""

    def _score_output(self, result: str, context: list) -> float:
        """Score output based on grounding and structure."""
        if not result.strip():
            return 0.0

        score = 0.5  # Base score for non-empty output

        # Bonus for having bullets (lines starting with - or *)
        lines = result.strip().split("\n")
        bullet_lines = [l for l in lines if l.strip().startswith(("-", "*", "•"))]
        if bullet_lines:
            score += 0.2

        # Bonus for metrics/numbers
        if any(char.isdigit() for char in result):
            score += 0.15

        # Bonus for good grounding (sources available)
        if context:
            score += 0.15

        return min(score, 1.0)
