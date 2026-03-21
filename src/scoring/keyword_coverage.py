"""Keyword Coverage Scorer — Measures keyword overlap between resume and JD."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger()


@dataclass
class KeywordCoverageResult:
    """Result of keyword coverage analysis."""

    coverage_score: float
    matched_keywords: list[str]
    missing_keywords: list[str]
    keyword_density: dict[str, int]  # keyword -> count in resume


class KeywordCoverageScorer:
    """Analyzes keyword coverage between resume and JD for ATS optimization."""

    # Common non-meaningful words to exclude
    STOP_WORDS = {
        "the", "and", "for", "with", "that", "this", "from", "have", "been",
        "will", "are", "was", "were", "has", "had", "not", "but", "can",
        "our", "your", "their", "about", "into", "than", "other", "its",
        "you", "who", "what", "how", "why", "all", "each", "every",
        "more", "most", "some", "such", "only", "own", "same", "also",
        "should", "would", "could", "may", "must", "shall", "being",
    }

    def score(
        self,
        resume_text: str,
        jd_text: str,
        min_keyword_length: int = 3,
    ) -> KeywordCoverageResult:
        """Score keyword coverage of resume relative to JD.

        Args:
            resume_text: Full resume text.
            jd_text: Full job description text.
            min_keyword_length: Minimum word length to consider.

        Returns:
            KeywordCoverageResult with coverage metrics.
        """
        jd_keywords = self._extract_keywords(jd_text, min_keyword_length)
        resume_words = set(re.findall(r"\b[a-zA-Z]{3,}\b", resume_text.lower()))

        matched = [kw for kw in jd_keywords if kw in resume_words]
        missing = [kw for kw in jd_keywords if kw not in resume_words]

        # Keyword density in resume
        density: dict[str, int] = {}
        for kw in matched:
            count = len(re.findall(rf"\b{re.escape(kw)}\b", resume_text.lower()))
            density[kw] = count

        coverage = len(matched) / max(len(jd_keywords), 1)

        logger.info(
            "keyword_coverage.scored",
            coverage=round(coverage, 3),
            matched=len(matched),
            missing=len(missing),
        )
        return KeywordCoverageResult(
            coverage_score=coverage,
            matched_keywords=matched,
            missing_keywords=missing,
            keyword_density=density,
        )

    def _extract_keywords(self, text: str, min_length: int) -> list[str]:
        """Extract meaningful keywords from text."""
        words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
        from collections import Counter
        counts = Counter(w for w in words if w not in self.STOP_WORDS and len(w) >= min_length)
        # Return keywords appearing 2+ times, or all if fewer than 10
        frequent = [w for w, c in counts.most_common(50) if c >= 2]
        if len(frequent) < 10:
            frequent = [w for w, _ in counts.most_common(30)]
        return frequent
