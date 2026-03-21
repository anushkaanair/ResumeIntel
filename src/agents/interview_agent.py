"""Interview Agent — Generates interview preparation materials from optimized resume."""

from __future__ import annotations

import structlog

from src.agents.base_agent import AgentInput, AgentOutput, BaseAgent
from src.exceptions import QualityGateError
from src.rag.retriever import Retriever

logger = structlog.get_logger()


class InterviewAgent(BaseAgent):
    """Generates interview prep questions and talking points based on resume + JD."""

    QUALITY_THRESHOLD = 0.6
    MAX_RETRIES = 3

    def __init__(self, retriever: Retriever, llm_client: object) -> None:
        self.retriever = retriever
        self.llm = llm_client

    async def execute(self, input: AgentInput) -> AgentOutput:
        self.validate_input(input)

        # RAG: retrieve experience segments for interview prep
        context = await self.retriever.retrieve(
            query=f"interview questions for {input.job_description[:200]}",
            top_k=10,
        )

        prompt = self._build_prompt(input, context)
        prep_material = await self.llm.generate(prompt)

        output = AgentOutput(
            content=prep_material,
            quality_score=self._score_prep(prep_material),
            sources=context,
            metadata={"type": "interview_prep"},
        )
        self.validate_output(output)
        return output

    def validate_input(self, input: AgentInput) -> None:
        if not input.content:
            raise ValueError("No resume content for interview prep")

    def validate_output(self, output: AgentOutput) -> None:
        if output.quality_score < self.QUALITY_THRESHOLD:
            raise QualityGateError(
                f"Interview prep quality {output.quality_score:.2f} below threshold"
            )

    def _build_prompt(self, input: AgentInput, context: list) -> str:
        context_text = "\n".join(f"- {seg.content}" for seg in context)

        return f"""Generate comprehensive interview preparation based on this resume and job description.

RESUME:
{input.content[:3000]}

JOB DESCRIPTION:
{input.job_description or "General interview preparation"}

RELEVANT EXPERIENCE SEGMENTS:
{context_text}

Generate:
1. **Behavioral Questions** (5-7 STAR-format questions based on resume experiences)
2. **Technical Questions** (5-7 questions matching JD technical requirements)
3. **Talking Points** (key achievements to highlight, with specific metrics from resume)
4. **Questions to Ask** (3-5 insightful questions about the role/company)

For each behavioral question, include a suggested STAR response framework using
actual experiences from the resume. Never fabricate — use only source data."""

    def _score_prep(self, content: str) -> float:
        """Score interview prep completeness."""
        if not content.strip():
            return 0.0

        score = 0.4
        lower = content.lower()

        if "behavioral" in lower or "star" in lower:
            score += 0.15
        if "technical" in lower:
            score += 0.15
        if "talking point" in lower:
            score += 0.15
        if "questions to ask" in lower or "ask the interviewer" in lower:
            score += 0.15

        return min(score, 1.0)
