"""Ingestion Agent — Parses resume into structured segments and indexes them."""

from __future__ import annotations

from typing import Any

import structlog

from src.agents.base_agent import AgentInput, AgentOutput, BaseAgent, RetrievedSegment
from src.exceptions import QualityGateError
from src.rag.retriever import Retriever

logger = structlog.get_logger()

# Standard resume section headers to detect
SECTION_HEADERS = [
    "summary", "objective", "experience", "work experience", "education",
    "skills", "technical skills", "projects", "certifications", "awards",
    "publications", "volunteer", "languages", "interests",
]


class IngestionAgent(BaseAgent):
    """Parses raw resume text into structured sections and indexes segments for RAG."""

    QUALITY_THRESHOLD = 0.6
    MAX_RETRIES = 3

    def __init__(self, retriever: Retriever) -> None:
        self.retriever = retriever

    async def execute(self, input: AgentInput) -> AgentOutput:
        self.validate_input(input)

        sections = self._extract_sections(input.content)
        segments = self._create_segments(sections)

        # Index segments for RAG retrieval
        await self.retriever.index_segments(segments)

        quality_score = self._calculate_quality(sections)

        output = AgentOutput(
            content=input.content,
            quality_score=quality_score,
            sections=sections,
            metadata={
                "segment_count": len(segments),
                "section_count": len(sections),
                "detected_sections": list(sections.keys()),
            },
        )
        self.validate_output(output)
        return output

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

    def _extract_sections(self, text: str) -> dict[str, str]:
        """Extract named sections from resume text."""
        sections: dict[str, str] = {}
        current_section = "header"
        current_content: list[str] = []

        for line in text.split("\n"):
            stripped = line.strip().lower()
            matched_header = None
            for header in SECTION_HEADERS:
                if stripped.startswith(header) or stripped == header:
                    matched_header = header
                    break

            if matched_header:
                if current_content:
                    sections[current_section] = "\n".join(current_content).strip()
                current_section = matched_header
                current_content = []
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

    def _calculate_quality(self, sections: dict[str, str]) -> float:
        """Score ingestion quality based on section coverage."""
        important_sections = {"experience", "work experience", "education", "skills"}
        found = sum(1 for s in sections if s in important_sections)
        return min(found / max(len(important_sections) - 1, 1), 1.0)
