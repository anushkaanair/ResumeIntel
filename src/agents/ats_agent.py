"""ATS compatibility check — a rule-based approximation of Workday, Greenhouse, Lever and Taleo.

This is a heuristic, not the vendors' parsers (which are not public). It checks the
things those systems are widely documented to be sensitive to — section headers,
date formats, special characters, bullet length, contact header — plus how many of
the JD's key skills the resume actually mentions. Treat it as a formatting checklist.
"""

from __future__ import annotations

import re
from typing import Any

import structlog

from src.agents.base_agent import AgentInput, AgentOutput, BaseAgent, Provenance
from src.exceptions import QualityGateError
from src.rag.retriever import Retriever
from src.scoring.keywords import extract_jd_keywords, terms_in

logger = structlog.get_logger()

# Platform-specific parsing quirks and keyword requirements
ATS_PLATFORM_PROFILES: dict[str, dict[str, Any]] = {
    "workday": {
        "required_sections": ["experience", "education", "skills"],
        "date_format_pattern": r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}\b",
        "max_bullet_length": 200,
        "penalized_chars": ["&", "@", "#"],
        "strict_header_parse": True,
    },
    "greenhouse": {
        "required_sections": ["experience", "education"],
        "date_format_pattern": r"\b\d{4}\b",
        "max_bullet_length": 500,
        "penalized_chars": [],
        "strict_header_parse": False,
    },
    "lever": {
        "required_sections": ["experience", "skills"],
        "date_format_pattern": r"\b\d{4}\b",
        "max_bullet_length": 300,
        "penalized_chars": ["#", "•"],
        "strict_header_parse": False,
    },
    "taleo": {
        "required_sections": ["experience", "education", "skills", "summary"],
        "date_format_pattern": r"\b(0?[1-9]|1[0-2])/\d{4}\b",
        "max_bullet_length": 150,
        "penalized_chars": ["•", "–", "—", "&"],
        "strict_header_parse": True,
    },
}

SECTION_ALIASES = {
    "experience": ["experience", "work experience", "professional experience", "employment"],
    "education": ["education", "academic", "academics"],
    "skills": ["skills", "technical skills", "core competencies", "technologies"],
    "summary": ["summary", "professional summary", "about", "objective", "profile"],
}


class ATSAgent(BaseAgent):
    """Rule-based ATS compatibility check across four platform profiles (heuristic)."""

    # A low heuristic score is a finding to report, not a failure to retry.
    QUALITY_THRESHOLD = 0.0
    MAX_RETRIES = 1

    def __init__(self, retriever: Retriever, llm_client: object) -> None:
        self.retriever = retriever
        self.llm = llm_client

    async def execute(self, input: AgentInput) -> AgentOutput:
        context = await self.retriever.retrieve(query=input.job_description or input.content, top_k=5)
        chunk_ids = [seg.segment_id for seg in context]

        jd_keywords = self._extract_jd_keywords(input.job_description)
        detected_sections = self._detect_sections(input.content)
        bullets = self._extract_bullets(input.content)

        platform_reports: dict[str, Any] = {}
        overall_scores: list[float] = []

        for platform, profile in ATS_PLATFORM_PROFILES.items():
            report = self._simulate_platform(
                platform, profile, input.content, jd_keywords, detected_sections, bullets
            )
            platform_reports[platform] = report
            overall_scores.append(report["parse_accuracy"])

        aggregate_score = sum(overall_scores) / len(overall_scores)

        # Use LLM to generate actionable ATS improvement suggestions
        suggestions = await self._generate_suggestions(input, platform_reports, context)

        provenance = Provenance(
            agent_name="ATSAgent",
            input_summary=input.content[:200],
            retrieved_chunk_ids=chunk_ids,
            decision_rationale=(
                f"Rule-based ATS compatibility check over 4 platform profiles (heuristic, not vendor parsers). "
                f"Average compatibility: {aggregate_score:.2f}. "
                f"Detected sections: {detected_sections}."
            ),
            confidence=aggregate_score,
        )

        return AgentOutput(
            content=input.content,  # ATS agent doesn't rewrite, only analyzes
            quality_score=aggregate_score,
            sources=context,
            provenance=provenance,
            suggestions=suggestions,
            metadata={
                "platform_reports": platform_reports,
                "detected_sections": detected_sections,
                "jd_keyword_count": len(jd_keywords),
                "aggregate_ats_score": aggregate_score,
                "method": "rule-based heuristic; not the vendors' real parsers",
            },
        )

    def _simulate_platform(
        self,
        platform: str,
        profile: dict[str, Any],
        content: str,
        jd_keywords: set[str],
        detected_sections: list[str],
        bullets: list[str],
    ) -> dict[str, Any]:
        warnings: list[str] = []

        # Section detection accuracy
        required = profile["required_sections"]
        found = [s for s in required if s in detected_sections]
        section_accuracy = len(found) / max(len(required), 1)

        missing_sections = [s for s in required if s not in detected_sections]
        if missing_sections:
            warnings.append(f"Missing required sections: {', '.join(missing_sections)}")

        # Date format compliance
        date_pattern = profile["date_format_pattern"]
        has_dates = bool(re.search(date_pattern, content))
        if not has_dates:
            warnings.append(f"No {platform}-compatible date format detected (expected: {date_pattern})")

        # Penalized characters
        for char in profile["penalized_chars"]:
            if char in content:
                warnings.append(f"Penalized character '{char}' found — may cause parse errors in {platform}")

        # Bullet length compliance
        max_len = profile["max_bullet_length"]
        long_bullets = [b for b in bullets if len(b) > max_len]
        if long_bullets:
            warnings.append(f"{len(long_bullets)} bullet(s) exceed {platform} max length of {max_len} chars")

        # Keyword match rate against JD
        keyword_match_rate: float | None
        if jd_keywords:
            matched = jd_keywords & terms_in(content)
            keyword_match_rate = len(matched) / len(jd_keywords)
            if keyword_match_rate < 0.4:
                absent = sorted(jd_keywords - matched)[:6]
                warnings.append(
                    f"Resume mentions only {keyword_match_rate:.0%} of the JD's key skills "
                    f"(absent: {', '.join(absent)}). Add them only if you have them."
                )
        else:
            keyword_match_rate = None  # JD has no recognisable skill terms; don't invent a score

        # Header strictness check
        if profile["strict_header_parse"]:
            email_found = bool(re.search(r"[\w.+-]+@[\w.-]+\.\w{2,}", content))
            if not email_found:
                warnings.append(f"{platform} strict parser requires email in contact header")

        if keyword_match_rate is None:
            parse_accuracy = (section_accuracy * 0.7) + (0.3 if has_dates else 0.0)
        else:
            parse_accuracy = (section_accuracy * 0.4) + (keyword_match_rate * 0.4) + (0.2 if has_dates else 0.0)

        return {
            "platform": platform,
            "parse_accuracy": round(parse_accuracy, 3),
            "keyword_match_rate": None if keyword_match_rate is None else round(keyword_match_rate, 3),
            "sections_detected": found,
            "warnings": warnings,
        }

    async def _generate_suggestions(
        self, input: AgentInput, reports: dict[str, Any], context: list
    ) -> list[str]:
        all_warnings: list[str] = []
        for report in reports.values():
            all_warnings.extend(report["warnings"])

        if not all_warnings:
            return ["Resume passes all ATS checks."]

        context_text = "\n".join(f"- {seg.content}" for seg in context[:3])
        prompt = f"""You are an ATS optimization expert. Based on these ATS warnings, provide 3-5 concise, actionable fixes.

ATS WARNINGS:
{chr(10).join(f'- {w}' for w in all_warnings[:10])}

RESUME CONTEXT:
{context_text}

Return a numbered list of specific fixes. One sentence each. No fabrication."""

        result = await self.llm.generate(prompt)
        lines = [l.strip() for l in result.strip().splitlines() if l.strip() and l.strip()[0].isdigit()]
        return lines if lines else [result.strip()]

    def _extract_jd_keywords(self, jd: str) -> set[str]:
        """The JD's key skills (ranked vocabulary match), not every word in it."""
        return {k.term for k in extract_jd_keywords(jd, limit=25)}

    def _detect_sections(self, content: str) -> list[str]:
        found: list[str] = []
        content_lower = content.lower()
        for canonical, aliases in SECTION_ALIASES.items():
            if any(alias in content_lower for alias in aliases):
                found.append(canonical)
        return found

    def _extract_bullets(self, content: str) -> list[str]:
        return [
            line.strip()
            for line in content.split("\n")
            if line.strip().startswith(("-", "*", "•"))
        ]

    def validate_input(self, input: AgentInput) -> None:
        if not input.content:
            raise ValueError("No resume content for ATS simulation")

    def validate_output(self, output: AgentOutput) -> None:
        if "aggregate_ats_score" not in output.metadata:
            raise QualityGateError("ATS simulation produced no aggregate score")
