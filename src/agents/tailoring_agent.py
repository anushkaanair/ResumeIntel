"""Tailoring Agent — Tailors resume content to match a specific job description.

Alignment Gate: Before tailoring runs, cosine similarity between the resume
embedding and JD embedding is computed via SBERT. If score < ALIGNMENT_THRESHOLD
the agent aborts early and returns status="alignment_gate_failed" with the
three weakest resume sections ranked by semantic distance from the JD.
"""

from __future__ import annotations

import re

import numpy as np
import structlog
from sklearn.metrics.pairwise import cosine_similarity

from src.agents.base_agent import AgentInput, AgentOutput, BaseAgent, Provenance
from src.config.industry_profiles import IndustryProfile, classify_profile
from src.exceptions import QualityGateError
from src.rag.embedder import Embedder
from src.rag.retriever import Retriever

logger = structlog.get_logger()

ALIGNMENT_THRESHOLD = 0.6


class TailoringAgent(BaseAgent):
    """Tailors resume to maximize alignment with a target job description.

    Hard gate: if the resume-JD cosine similarity is below ALIGNMENT_THRESHOLD,
    tailoring is aborted and the three weakest sections are returned so the
    frontend/API can surface actionable guidance to the user.
    """

    QUALITY_THRESHOLD = 0.7
    MAX_RETRIES = 3

    def __init__(
        self,
        retriever: Retriever,
        llm_client: object,
        industry_profile: IndustryProfile | None = None,
    ) -> None:
        self.retriever = retriever
        self.llm = llm_client
        self.embedder = Embedder()
        self._forced_profile = industry_profile  # manual override from API

    async def execute(self, input: AgentInput) -> AgentOutput:
        # ------------------------------------------------------------------
        # Alignment gate — compute SBERT cosine similarity before any LLM call
        # ------------------------------------------------------------------
        resume_embedding = self.embedder.encode_single(input.content)
        jd_embedding = self.embedder.encode_single(input.job_description)

        alignment_score = float(
            cosine_similarity(
                resume_embedding.reshape(1, -1),
                jd_embedding.reshape(1, -1),
            )[0][0]
        )

        logger.info(
            "tailoring_agent.alignment_check",
            score=round(alignment_score, 4),
            threshold=ALIGNMENT_THRESHOLD,
        )

        if alignment_score < ALIGNMENT_THRESHOLD:
            weakest = self._rank_sections_by_distance(
                input.sections or self._extract_sections(input.content),
                jd_embedding,
            )
            logger.warning(
                "tailoring_agent.alignment_gate_failed",
                score=round(alignment_score, 4),
                weakest_sections=[s["section"] for s in weakest],
            )
            return AgentOutput(
                content=input.content,  # pass through unchanged
                quality_score=alignment_score,
                status="alignment_gate_failed",
                metadata={
                    "alignment_score": round(alignment_score, 4),
                    "threshold": ALIGNMENT_THRESHOLD,
                    "weakest_sections": weakest,
                    "message": (
                        f"Alignment score {alignment_score:.2f} is below threshold "
                        f"{ALIGNMENT_THRESHOLD}. Tailoring aborted."
                    ),
                },
            )

        # ------------------------------------------------------------------
        # Normal tailoring path
        # ------------------------------------------------------------------
        profile = self._forced_profile or classify_profile(input.job_description)
        logger.info("tailoring_agent.profile_selected", profile=profile.name)
        return await self._run_tailoring(input, alignment_score, profile)

    def validate_input(self, input: AgentInput) -> None:
        if not input.content:
            raise ValueError("No resume content to tailor")
        if not input.job_description:
            raise ValueError("Job description required for tailoring")

    def validate_output(self, output: AgentOutput) -> None:
        # Alignment gate failures are intentional early returns — not gate violations.
        if output.status == "alignment_gate_failed":
            return
        if output.quality_score < self.QUALITY_THRESHOLD:
            raise QualityGateError(
                f"Tailoring alignment {output.quality_score:.2f} below threshold"
            )

    # ------------------------------------------------------------------
    # Alignment gate helpers
    # ------------------------------------------------------------------

    def _rank_sections_by_distance(
        self, sections: dict[str, str], jd_embedding: np.ndarray
    ) -> list[dict]:
        """Return sections sorted by ascending similarity to JD (worst first)."""
        ranked: list[dict] = []
        for section_name, section_text in sections.items():
            if not section_text.strip():
                continue
            sec_embedding = self.embedder.encode_single(section_text)
            score = float(
                cosine_similarity(
                    sec_embedding.reshape(1, -1),
                    jd_embedding.reshape(1, -1),
                )[0][0]
            )
            ranked.append({"section": section_name, "alignment_score": round(score, 4)})
        ranked.sort(key=lambda x: x["alignment_score"])
        return ranked[:3]  # top-3 weakest

    def _extract_sections(self, content: str) -> dict[str, str]:
        """Fallback: extract sections from raw markdown when sections dict is empty."""
        sections: dict[str, str] = {}
        current_section = "general"
        current_lines: list[str] = []

        for line in content.split("\n"):
            if line.startswith("## "):
                if current_lines:
                    sections[current_section] = "\n".join(current_lines)
                current_section = line.lstrip("# ").strip().lower()
                current_lines = []
            else:
                current_lines.append(line)

        if current_lines:
            sections[current_section] = "\n".join(current_lines)

        return sections

    # ------------------------------------------------------------------
    # Normal tailoring path
    # ------------------------------------------------------------------

    async def _run_tailoring(
        self, input: AgentInput, alignment_score: float, profile: IndustryProfile | None = None
    ) -> AgentOutput:
        context = await self.retriever.retrieve(query=input.job_description, top_k=10)

        weaknesses: list[str] = []
        if input.previous_output:
            weaknesses = input.previous_output.suggestions

        prompt = self._build_prompt(input, context, weaknesses, profile)
        tailored = await self.llm.generate(prompt)

        final_alignment = self._calculate_alignment(tailored, input.job_description)

        return AgentOutput(
            content=tailored,
            quality_score=final_alignment,
            sources=context,
            status="ok",
            metadata={
                "alignment_score": round(final_alignment, 4),
                "pre_tailoring_alignment": round(alignment_score, 4),
                "weaknesses_addressed": len(weaknesses),
                "industry_profile": profile.name if profile else "tech_swe",
            },
            provenance=Provenance(
                agent_name="tailoring",
                input_summary=input.content[:200],
                retrieved_chunks=[seg.segment_id for seg in context],
                decision_rationale=(
                    f"Pre-tailoring alignment: {alignment_score:.2f}. "
                    f"Post-tailoring alignment: {final_alignment:.2f}. "
                    f"Addressed {len(weaknesses)} weaknesses from prior agents."
                ),
                confidence=final_alignment,
            ),
        )

    def _build_prompt(
        self,
        input: AgentInput,
        context: list,
        weaknesses: list[str],
        profile: IndustryProfile | None = None,
    ) -> str:
        context_text = "\n".join(
            f"- {seg.content} (score: {seg.score:.2f})" for seg in context
        )
        weakness_text = "\n".join(f"- {w}" for w in weaknesses) if weaknesses else "None detected"

        tone_note = f"\nTONE FOR THIS INDUSTRY ({profile.display_name}): {profile.tone}" if profile else ""
        return f"""You are an expert resume tailoring specialist.{tone_note} Your task is to customize this resume to maximize
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
