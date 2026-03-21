"""Tailoring Agent — Tailors resume content to match a specific job description."""

from __future__ import annotations

import structlog

from src.agents.base_agent import AgentInput, AgentOutput, BaseAgent
from src.exceptions import QualityGateError
from src.rag.retriever import Retriever

logger = structlog.get_logger()


class TailoringAgent(BaseAgent):
    """Tailors resume to maximize alignment with a target job description."""

    QUALITY_THRESHOLD = 0.7
    MAX_RETRIES = 3

    def __init__(self, retriever: Retriever, llm_client: object) -> None:
        self.retriever = retriever
        self.llm = llm_client

    async def execute(self, input: AgentInput) -> AgentOutput:
        self.validate_input(input)

        # RAG: retrieve JD-aligned segments
        context = await self.retriever.retrieve(
            query=input.job_description,
            top_k=10,
        )

        # Get weakness suggestions from previous agent if available
        weaknesses = []
        if input.previous_output:
            weaknesses = input.previous_output.suggestions

        prompt = self._build_prompt(input, context, weaknesses)
        tailored = await self.llm.generate(prompt)

        alignment_score = self._calculate_alignment(tailored, input.job_description)

        output = AgentOutput(
            content=tailored,
            quality_score=alignment_score,
            sources=context,
            metadata={
                "alignment_score": alignment_score,
                "weaknesses_addressed": len(weaknesses),
            },
        )
        self.validate_output(output)
        return output

    def validate_input(self, input: AgentInput) -> None:
        if not input.content:
            raise ValueError("No resume content to tailor")
        if not input.job_description:
            raise ValueError("Job description required for tailoring")

    def validate_output(self, output: AgentOutput) -> None:
        if output.quality_score < self.QUALITY_THRESHOLD:
            raise QualityGateError(
                f"Tailoring alignment {output.quality_score:.2f} below threshold"
            )

    def _build_prompt(self, input: AgentInput, context: list, weaknesses: list[str]) -> str:
        context_text = "\n".join(
            f"- {seg.content} (score: {seg.score:.2f})" for seg in context
        )
        weakness_text = "\n".join(f"- {w}" for w in weaknesses) if weaknesses else "None detected"

        return f"""You are an expert resume tailoring specialist. Modify this resume to maximize
alignment with the target job description while maintaining truthfulness.

RULES:
- Reorder and emphasize experiences matching JD requirements
- Incorporate JD keywords naturally into existing bullets
- Address detected weaknesses
- NEVER fabricate experience, metrics, or skills not in the source data
- Maintain professional tone and ATS-friendly formatting

CURRENT RESUME:
{input.content}

TARGET JOB DESCRIPTION:
{input.job_description}

RELEVANT SOURCE SEGMENTS (RAG):
{context_text}

WEAKNESSES TO ADDRESS:
{weakness_text}

Return the full tailored resume in markdown format."""

    def _calculate_alignment(self, tailored: str, jd: str) -> float:
        """Calculate keyword alignment between tailored resume and JD."""
        import re

        jd_words = set(re.findall(r"\b[a-zA-Z]{3,}\b", jd.lower()))
        resume_words = set(re.findall(r"\b[a-zA-Z]{3,}\b", tailored.lower()))

        stop_words = {
            "the", "and", "for", "with", "that", "this", "from", "have",
            "been", "will", "are", "was", "not", "but", "can", "our",
        }
        jd_keywords = jd_words - stop_words
        if not jd_keywords:
            return 0.7

        overlap = jd_keywords & resume_words
        return min(len(overlap) / len(jd_keywords), 1.0)
