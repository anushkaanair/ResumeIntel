"""Tailoring Agent — Tailors resume content to match a specific job description."""

from __future__ import annotations

import re

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

        return AgentOutput(
            content=tailored,
            quality_score=alignment_score,
            sources=context,
            metadata={
                "alignment_score": alignment_score,
                "weaknesses_addressed": len(weaknesses),
            },
        )

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

        return f"""You are an expert resume tailoring specialist. Your task is to customize this resume to maximize
its alignment with a specific job description, while remaining strictly truthful to the candidate's actual experience.

TAILORING RULES — ALL MANDATORY:
1. KEYWORD INTEGRATION: Weave JD keywords into existing bullets naturally. Prefer exact phrases from the JD where they are honest.
2. REORDERING: Place the most JD-relevant experience, projects, and skills first within each section.
3. EMPHASIS: Expand bullets that directly match JD requirements. Condense or trim bullets for unrelated experience.
4. SKILLS SECTION: Reorder skills to front-load those mentioned in the JD. Do not add skills the candidate does not have.
5. SUMMARY/OBJECTIVE: If present, rewrite to mirror the job title and key requirements from the JD.
6. ANTI-FABRICATION (non-negotiable): Do NOT add any experience, skill, tool, metric, certification, or achievement not present in the current resume. Adding false claims is grounds for rejection.
7. FORMAT: Return the complete resume in markdown. Use ## for section headings and - for bullets. Preserve all contact information exactly.

WEAKNESSES TO ADDRESS (from prior analysis):
{weakness_text}

CURRENT RESUME:
{input.content}

TARGET JOB DESCRIPTION:
{input.job_description}

HIGH-RELEVANCE SOURCE SEGMENTS (from RAG — use for grounding edits):
{context_text}

Return the COMPLETE tailored resume. Do not omit any section. Every change must be traceable to either the JD requirements or the candidate's actual source data above."""

    def _calculate_alignment(self, tailored: str, jd: str) -> float:
        """Calculate keyword alignment between tailored resume and JD."""
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
