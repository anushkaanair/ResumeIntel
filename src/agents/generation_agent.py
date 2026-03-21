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
        # RAG: retrieve relevant context from indexed resume segments
        context = await self.retriever.retrieve(
            query=input.job_description or input.content,
            top_k=10,
        )

        prompt = self._build_prompt(input, context)
        result = await self.llm.generate(prompt)

        return AgentOutput(
            content=result,
            quality_score=self._score_output(result, context),
            sources=context,
            metadata={"grounded": True, "source_count": len(context)},
        )

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

        return f"""You are an expert resume writer specializing in ATS optimization for competitive tech roles.
Your task is to rewrite resume bullets to maximize impact, clarity, and ATS keyword alignment.

STRICT RULES — MUST FOLLOW:
1. GROUNDING: Every bullet must trace directly to the source data. Do not invent projects, metrics, tools, or achievements.
2. ACTION VERBS: Start every bullet with a strong past-tense action verb (Led, Designed, Implemented, Built, Architected, Optimized, Delivered, Automated, Reduced, Increased, Launched, Migrated, Scaled, Streamlined).
3. METRICS: Include numbers wherever the source data contains them (%, $, x, users, requests/day, ms, etc.). If no metric is in the source, do NOT fabricate one.
4. KEYWORDS: Naturally incorporate relevant terms from the job description into bullets — do not keyword-stuff.
5. LENGTH: Each bullet should be 1–2 lines. No sub-bullets. No generic filler phrases like "responsible for" or "worked on".
6. COMPLETENESS: Output ALL sections present in the source — do not drop any section.
7. HEADER: Preserve the candidate name, contact info, and title exactly as given — do not modify.

SOURCE RESUME DATA (authoritative — do not contradict):
{sections_text}

RETRIEVED CONTEXT (high-relevance segments from RAG — use these for grounding):
{context_text}

TARGET JOB DESCRIPTION:
{input.job_description or "General optimization — improve impact and clarity for software engineering roles"}

OUTPUT FORMAT:
Return the full resume with each section as a markdown heading (## Section Name) followed by bullet points (- bullet text).
Example:
## Experience
- Led migration of legacy monolith to microservices, reducing p99 latency by 40%

## Skills
Python, FastAPI, PostgreSQL, Docker, AWS"""

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
