"""Weak Detection Agent — Identifies weak areas in resume content."""

from __future__ import annotations

import re

import structlog

from src.agents.base_agent import AgentInput, AgentOutput, BaseAgent
from src.exceptions import QualityGateError
from src.rag.retriever import Retriever

logger = structlog.get_logger()


class WeakDetectionAgent(BaseAgent):
    """Detects weak sections, missing keywords, and gaps relative to a job description."""

    QUALITY_THRESHOLD = 0.6
    MAX_RETRIES = 3

    def __init__(self, retriever: Retriever, llm_client: object) -> None:
        self.retriever = retriever
        self.llm = llm_client

    async def execute(self, input: AgentInput) -> AgentOutput:
        self.validate_input(input)

        # RAG: retrieve JD-relevant segments to compare
        context = await self.retriever.retrieve(
            query=input.job_description,
            top_k=10,
        )

        weaknesses = self._detect_weaknesses(input, context)

        prompt = self._build_prompt(input, weaknesses, context)
        analysis = await self.llm.generate(prompt)

        output = AgentOutput(
            content=analysis,
            quality_score=self._score_detection(weaknesses),
            sources=context,
            suggestions=weaknesses,
            metadata={
                "weakness_count": len(weaknesses),
                "coverage_gaps": self._find_keyword_gaps(input),
            },
        )
        self.validate_output(output)
        return output

    def validate_input(self, input: AgentInput) -> None:
        if not input.content:
            raise ValueError("No resume content to analyze")
        if not input.job_description:
            raise ValueError("Job description required for weakness detection")

    def validate_output(self, output: AgentOutput) -> None:
        if output.quality_score < self.QUALITY_THRESHOLD:
            raise QualityGateError(
                f"Detection quality {output.quality_score:.2f} below threshold"
            )

    def _detect_weaknesses(self, input: AgentInput, context: list) -> list[str]:
        """Detect specific weaknesses in the resume."""
        weaknesses: list[str] = []

        # Check keyword coverage
        gaps = self._find_keyword_gaps(input)
        if gaps:
            weaknesses.append(f"Missing keywords from JD: {', '.join(gaps[:10])}")

        # Check section completeness
        sections = input.sections or (
            input.previous_output.sections if input.previous_output else {}
        )
        if "skills" not in sections and "technical skills" not in sections:
            weaknesses.append("Missing skills/technical skills section")
        if "experience" not in sections and "work experience" not in sections:
            weaknesses.append("Missing experience section")

        # Check for vague bullets
        bullets = [
            l.strip() for l in input.content.split("\n")
            if l.strip().startswith(("-", "*", "•"))
        ]
        vague = [b for b in bullets if len(b) < 30]
        if vague:
            weaknesses.append(f"{len(vague)} bullets are too vague or short")

        # Check RAG coverage (low-scoring retrievals = poor alignment)
        low_score = [s for s in context if s.score < 0.5]
        if len(low_score) > len(context) * 0.5:
            weaknesses.append("Resume content has low alignment with JD requirements")

        return weaknesses

    def _find_keyword_gaps(self, input: AgentInput) -> list[str]:
        """Find JD keywords missing from resume."""
        if not input.job_description:
            return []

        jd_words = set(re.findall(r"\b[a-zA-Z]{3,}\b", input.job_description.lower()))
        resume_words = set(re.findall(r"\b[a-zA-Z]{3,}\b", input.content.lower()))

        # Filter to meaningful technical/skill keywords
        stop_words = {
            "the", "and", "for", "with", "that", "this", "from", "have", "been",
            "will", "are", "was", "were", "has", "had", "not", "but", "can",
            "our", "your", "their", "about", "into", "than", "other", "its",
            "also", "should", "would", "could", "may", "must", "shall",
        }
        jd_keywords = jd_words - stop_words - resume_words

        return sorted(jd_keywords)[:20]

    def _build_prompt(self, input: AgentInput, weaknesses: list[str], context: list) -> str:
        context_text = "\n".join(f"- {seg.content}" for seg in context[:5])
        weakness_text = "\n".join(f"- {w}" for w in weaknesses)

        return f"""Analyze this resume for weaknesses relative to the target job description.

DETECTED WEAKNESSES:
{weakness_text}

RESUME CONTENT:
{input.content[:2000]}

JOB DESCRIPTION:
{input.job_description[:1000]}

RELEVANT SEGMENTS (from RAG):
{context_text}

Provide:
1. Priority-ranked list of weaknesses
2. Specific recommendations to address each
3. Keywords to add for better ATS alignment"""

    def _score_detection(self, weaknesses: list[str]) -> float:
        """Score based on thoroughness of detection."""
        # More weaknesses found = more thorough analysis
        if not weaknesses:
            return 0.6
        return min(0.6 + len(weaknesses) * 0.05, 1.0)
