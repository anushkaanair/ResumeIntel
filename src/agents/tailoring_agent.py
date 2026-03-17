"""Tailoring Agent — Tailors resume to JD with semantic alignment gate (patent claim 1c)."""

from __future__ import annotations

import re

import numpy as np
import structlog

from src.agents.base_agent import AgentInput, AgentOutput, BaseAgent, Provenance
from src.exceptions import QualityGateError
from src.rag.retriever import Retriever

logger = structlog.get_logger()

# Hard-abort threshold: cosine similarity between resume and JD embeddings
ALIGNMENT_THRESHOLD = 0.6


class AlignmentGateError(Exception):
    """Raised when resume-JD cosine similarity is below threshold."""

    def __init__(self, alignment_score: float, weak_sections: list[dict]) -> None:
        self.alignment_score = alignment_score
        self.weak_sections = weak_sections  # ranked list of {section, score}
        super().__init__(
            f"Alignment score {alignment_score:.3f} below threshold {ALIGNMENT_THRESHOLD}. "
            f"Weakest sections: {[s['section'] for s in weak_sections]}"
        )


class TailoringAgent(BaseAgent):
    """Tailors resume to maximize alignment with a target job description.

    Implements patent claim 1c: semantic alignment gate that aborts processing
    and returns ranked section-level deficiency when cosine similarity < 0.6.
    """

    QUALITY_THRESHOLD = 0.7
    MAX_RETRIES = 3

    def __init__(self, retriever: Retriever, llm_client: object) -> None:
        self.retriever = retriever
        self.llm = llm_client

    async def execute(self, input: AgentInput) -> AgentOutput:
        # ── Semantic Alignment Gate ──────────────────────────────────────────
        alignment_score, weak_sections = await self._check_alignment(input)
        if alignment_score < ALIGNMENT_THRESHOLD:
            logger.warning(
                "tailoring.alignment_gate_abort",
                score=alignment_score,
                weak_sections=[s["section"] for s in weak_sections],
            )
            raise AlignmentGateError(alignment_score, weak_sections)

        # ── Normal tailoring path ────────────────────────────────────────────
        context = await self.retriever.retrieve(query=input.job_description, top_k=10)
        chunk_ids = [seg.segment_id for seg in context]

        weaknesses = []
        if input.previous_output:
            weaknesses = input.previous_output.suggestions

        prompt = self._build_prompt(input, context, weaknesses)
        tailored = await self.llm.generate(prompt)

        final_score = self._calculate_alignment(tailored, input.job_description)

        provenance = Provenance(
            agent_name="TailoringAgent",
            input_summary=input.content[:200],
            retrieved_chunk_ids=chunk_ids,
            decision_rationale=(
                f"Pre-tailoring alignment: {alignment_score:.3f}. "
                f"Post-tailoring alignment: {final_score:.3f}."
            ),
            confidence=final_score,
        )

        return AgentOutput(
            content=tailored,
            quality_score=final_score,
            sources=context,
            provenance=provenance,
            metadata={
                "alignment_score": final_score,
                "pre_tailoring_alignment": alignment_score,
                "weaknesses_addressed": len(weaknesses),
            },
        )

    async def _check_alignment(self, input: AgentInput) -> tuple[float, list[dict]]:
        """Compute cosine similarity between full resume and JD embeddings.

        Returns (overall_score, ranked_weak_sections).
        """
        embedder = self.retriever.embedder

        resume_vec = embedder.encode_single(input.content)
        jd_vec = embedder.encode_single(input.job_description)
        # Vectors are already L2-normalized, so dot product = cosine similarity
        overall_score = float(np.dot(resume_vec, jd_vec))

        # Score each section individually to identify weakest ones
        section_scores: list[dict] = []
        for section_name, section_text in input.sections.items():
            if not section_text.strip():
                continue
            sec_vec = embedder.encode_single(section_text)
            sec_score = float(np.dot(sec_vec, jd_vec))
            section_scores.append({"section": section_name, "score": sec_score})

        # Sort ascending — weakest sections first (patent: ranked deficiency signal)
        section_scores.sort(key=lambda x: x["score"])
        return overall_score, section_scores[:3]

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

        ats_boost = input.metadata.get("ats_boost", False)
        current_ats = input.metadata.get("current_ats_score", 0.0)
        ats_section = ""
        if ats_boost:
            ats_section = f"""
ATS BOOST MODE — CURRENT ATS SCORE IS {int(current_ats * 100)}%. TARGET: 85%+:
8. KEYWORD DENSITY: Include every keyword from the JD requirements section verbatim. Repeat critical keywords naturally across multiple sections.
9. ATS FORMAT: Use only simple hyphens (-) for bullets. No special characters, tables, or text boxes. Format dates as "Month YYYY – Month YYYY".
10. SECTION HEADERS: Use only ATS-standard headers: Summary, Experience, Skills, Education, Projects, Certifications.
11. SKILLS SECTION: List every JD-required technology you possess. Use comma-separated one-word or short-phrase items.
12. ACTION VERBS: Start every bullet with a strong past-tense action verb (Led, Built, Designed, Optimized, Reduced, Increased).
13. QUANTIFY: Every bullet must contain at least one number, percentage, or measurable outcome.
"""

        return f"""You are an expert resume tailoring specialist. Customize this resume to maximize
alignment with the job description, while remaining strictly truthful.

TAILORING RULES — ALL MANDATORY:
1. KEYWORD INTEGRATION: Weave JD keywords into existing bullets naturally.
2. REORDERING: Place the most JD-relevant experience, projects, and skills first.
3. EMPHASIS: Expand bullets that match JD requirements. Condense unrelated experience.
4. SKILLS SECTION: Reorder to front-load skills mentioned in the JD.
5. SUMMARY/OBJECTIVE: If present, rewrite to mirror the job title and key requirements.
6. ANTI-FABRICATION (non-negotiable): Do NOT add any experience, skill, metric, or achievement
   not present in the current resume.
7. FORMAT: Return complete resume in markdown. ## for sections, - for bullets.
{ats_section}
WEAKNESSES TO ADDRESS:
{weakness_text}

CURRENT RESUME:
{input.content}

TARGET JOB DESCRIPTION:
{input.job_description}

HIGH-RELEVANCE SEGMENTS (from RAG):
{context_text}

Return the COMPLETE tailored resume. Do not omit any section."""

    def _calculate_alignment(self, tailored: str, jd: str) -> float:
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
