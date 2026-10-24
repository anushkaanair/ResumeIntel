"""Keyword Coverage Scorer — Measures keyword overlap between resume and JD."""

from __future__ import annotations

import re
from dataclasses import dataclass

import structlog

from src.scoring.keywords import extract_jd_keywords, term_counts, terms_in

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
        "experience", "work", "team", "ability", "strong", "skills", "role",
        "years", "including", "etc", "well", "new", "like", "using", "build",
    }

    def score(
        self,
        resume_text: str,
        jd_text: str | list[str],
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
        if isinstance(jd_text, (list, tuple)):  # callers have passed pre-split lines
            jd_text = "\n".join(jd_text)

        ranked = extract_jd_keywords(jd_text, limit=30)
        if ranked:
            have = terms_in(resume_text)
            counts = term_counts(resume_text)
            total = sum(k.score for k in ranked) or 1.0
            matched_terms = [k.term for k in ranked if k.term in have]
            missing_terms = [k.term for k in ranked if k.term not in have]
            coverage = sum(k.score for k in ranked if k.term in have) / total
            logger.info("keyword_coverage.scored", coverage=round(coverage, 3),
                        matched=len(matched_terms), missing=len(missing_terms))
            return KeywordCoverageResult(
                coverage_score=coverage,
                matched_keywords=matched_terms,
                missing_keywords=missing_terms,
                keyword_density={t: counts.get(t, 0) for t in matched_terms},
            )

        # No recognisable technical terms in the JD (e.g. a non-technical role):
        # fall back to generic word overlap.
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
