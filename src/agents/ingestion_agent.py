"""Ingestion Agent — Parses resume into structured segments and indexes them."""

from __future__ import annotations

from typing import Any

import structlog

from src.agents.base_agent import AgentInput, AgentOutput, BaseAgent, Provenance
from src.exceptions import QualityGateError
from src.rag.retriever import Retriever
from src.scoring.keywords import terms_in

logger = structlog.get_logger()

# Standard resume section headers to detect
SECTION_HEADERS = [
    "summary", "professional summary", "about", "about me", "profile", "objective",
    "experience", "work experience", "professional experience", "internships",
    "education", "academic", "academics",
    "skills", "technical skills", "core competencies", "technologies", "tech stack",
    "projects", "personal projects", "selected projects",
    "certifications", "awards", "honors", "achievements", "publications",
    "volunteer", "languages", "interests",
]

# Which detected headers count as evidence for each part of a usable resume.
_EXPERIENCE_LIKE = {
    "experience", "work experience", "professional experience", "internships",
    "projects", "personal projects", "selected projects",
}
_EDUCATION_LIKE = {"education", "academic", "academics"}
_SKILLS_LIKE = {"skills", "technical skills", "core competencies", "technologies", "tech stack"}
_BULLET_MARKS = ("-", "•", "*", "–", "—", "·")


class IngestionAgent(BaseAgent):
    """Parses raw resume text into structured sections and indexes segments for RAG."""

    QUALITY_THRESHOLD = 0.6
    # Section detection is deterministic: re-running it cannot change the score,
    # so retrying only re-indexes the same text. One attempt.
    MAX_RETRIES = 1

    def __init__(self, retriever: Retriever) -> None:
        self.retriever = retriever

    async def execute(self, input: AgentInput) -> AgentOutput:
        sections = self._extract_sections(input.content)
        segments = self._create_segments(sections)

        # Index segments for RAG retrieval
        await self.retriever.index_segments(segments)

        quality_score = self._calculate_quality(sections, input.content)

        provenance = Provenance(
            agent_name="IngestionAgent",
            input_summary=input.content[:200],
            retrieved_chunk_ids=[seg["segment_id"] for seg in segments],
            decision_rationale=(
                f"Detected {len(sections)} section(s): {', '.join(sections.keys())}. "
                f"Indexed {len(segments)} segment(s) into FAISS for downstream RAG retrieval."
            ),
            confidence=quality_score,
        )

        return AgentOutput(
            content=input.content,
            quality_score=quality_score,
            sections=sections,
            provenance=provenance,
            metadata={
                "segment_count": len(segments),
                "section_count": len(sections),
                "detected_sections": list(sections.keys()),
            },
        )

    def validate_input(self, input: AgentInput) -> None:
        if not input.content or len(input.content.strip()) < 50:
            raise ValueError("Resume content too short (minimum 50 characters)")

    def validate_output(self, output: AgentOutput) -> None:
        if output.quality_score < self.QUALITY_THRESHOLD:
            raise QualityGateError(
                f"Ingestion quality {output.quality_score:.2f} below threshold {self.QUALITY_THRESHOLD}"
            )
        if not output.sections:
            raise QualityGateError("No sections extracted from resume")

    @staticmethod
    def _match_header(line: str) -> tuple[str | None, str]:
        """Return (header, inline_remainder) if ``line`` is a section heading.

        A heading is a short line ("Experience", "Technical Skills", "Skills &
        Tools", "## Projects", or "Skills: Python, Go") — never a bullet and
        never a sentence that merely starts with a heading word.
        """
        raw = line.strip()
        if not raw or raw.startswith(_BULLET_MARKS):
            return None, ""
        raw = raw.lstrip("#").strip()
        head, sep, rest = raw.partition(":")
        if sep and len(head.split()) <= 3:
            candidate, remainder = head, rest.strip()
        else:
            candidate, remainder = raw, ""
        candidate = candidate.strip(" :*_|").lower()
        if not candidate or len(candidate) > 40 or len(candidate.split()) > 4:
            return None, ""
        for header in SECTION_HEADERS:
            if candidate == header or candidate.startswith(header + " "):
                # "Experience with Kafka and Spark" is a sentence, not a heading.
                if candidate != header and not remainder and len(candidate.split()) > 3:
                    continue
                return header, remainder
        return None, ""

    def _extract_sections(self, text: str) -> dict[str, str]:
        """Extract named sections from resume text."""
        sections: dict[str, str] = {}
        current_section = "header"
        current_content: list[str] = []

        for line in text.split("\n"):
            matched_header, remainder = self._match_header(line)

            if matched_header:
                if current_content:
                    sections[current_section] = "\n".join(current_content).strip()
                current_section = matched_header
                current_content = [remainder] if remainder else []
            else:
                current_content.append(line)

        if current_content:
            sections[current_section] = "\n".join(current_content).strip()

        return {k: v for k, v in sections.items() if v}

    def _create_segments(self, sections: dict[str, str]) -> list[dict[str, Any]]:
        """Break sections into indexable segments."""
        segments: list[dict[str, Any]] = []
        for section_name, content in sections.items():
            bullets = [b.strip() for b in content.split("\n") if b.strip()]
            for i, bullet in enumerate(bullets):
                segments.append({
                    "content": bullet,
                    "section": section_name,
                    "index": i,
                    "segment_id": f"{section_name}_{i}",
                })
        return segments

    def _calculate_quality(self, sections: dict[str, str], text: str = "") -> float:
        """Score how usable the parsed structure is (0..1).

        A resume needs something to optimise (experience or projects), an
        education entry, and evidence of skills — either a Skills section *or*
        technical terms in the text. A new-grad resume with no "Skills" header
        is normal and must not be rejected for it.
        """
        names = set(sections)
        has_experience = bool(names & _EXPERIENCE_LIKE)
        has_education = bool(names & _EDUCATION_LIKE)
        has_skills = bool(names & _SKILLS_LIKE) or len(terms_in(text or "\n".join(sections.values()))) >= 5
        return 0.4 * has_experience + 0.3 * has_education + 0.3 * has_skills
