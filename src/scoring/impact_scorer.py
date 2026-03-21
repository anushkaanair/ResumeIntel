"""Impact Scorer — Evaluates the impact quality of resume bullets."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger()

STRONG_VERBS = {
    "led", "designed", "implemented", "optimized", "delivered", "built",
    "architected", "automated", "reduced", "increased", "achieved",
    "launched", "migrated", "scaled", "streamlined", "orchestrated",
    "developed", "created", "engineered", "established", "spearheaded",
}

WEAK_VERBS = {
    "worked", "helped", "assisted", "participated", "was responsible",
    "handled", "dealt with", "involved in", "tasked with", "supported",
}


@dataclass
class BulletScore:
    """Score for a single resume bullet."""

    text: str
    score: float
    has_metric: bool
    has_strong_verb: bool
    has_weak_verb: bool
    suggestions: list[str] = field(default_factory=list)


@dataclass
class ImpactResult:
    """Result of impact scoring across all bullets."""

    overall_score: float
    bullet_scores: list[BulletScore]
    summary: dict[str, int]


class ImpactScorer:
    """Scores resume bullets for impact, action verbs, and quantification."""

    def score(self, content: str) -> ImpactResult:
        """Score all bullets in resume content for impact.

        Args:
            content: Resume text content.

        Returns:
            ImpactResult with per-bullet and overall scores.
        """
        bullets = self._extract_bullets(content)
        bullet_scores = [self._score_bullet(b) for b in bullets]

        overall = (
            sum(bs.score for bs in bullet_scores) / len(bullet_scores)
            if bullet_scores
            else 0.0
        )

        summary = {
            "total_bullets": len(bullet_scores),
            "with_metrics": sum(1 for bs in bullet_scores if bs.has_metric),
            "with_strong_verbs": sum(1 for bs in bullet_scores if bs.has_strong_verb),
            "with_weak_verbs": sum(1 for bs in bullet_scores if bs.has_weak_verb),
            "high_impact": sum(1 for bs in bullet_scores if bs.score >= 0.7),
            "low_impact": sum(1 for bs in bullet_scores if bs.score < 0.4),
        }

        logger.info("impact.scored", overall=round(overall, 3), **summary)
        return ImpactResult(
            overall_score=overall,
            bullet_scores=bullet_scores,
            summary=summary,
        )

    def _extract_bullets(self, content: str) -> list[str]:
        """Extract bullet points from content."""
        bullets = []
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith(("-", "*", "•", "–")):
                cleaned = re.sub(r"^[-*•–]\s*", "", stripped)
                if cleaned:
                    bullets.append(cleaned)
        return bullets

    def _score_bullet(self, bullet: str) -> BulletScore:
        """Score a single bullet for impact."""
        lower = bullet.lower()
        score = 0.3  # Base score

        has_metric = bool(re.search(r"\d+[%$KkMm]?|\$[\d,]+", bullet))
        has_strong_verb = any(v in lower.split()[:3] for v in STRONG_VERBS)
        has_weak_verb = any(v in lower for v in WEAK_VERBS)

        suggestions: list[str] = []

        if has_metric:
            score += 0.25
        else:
            suggestions.append("Add quantifiable metrics")

        if has_strong_verb:
            score += 0.25
        elif has_weak_verb:
            score += 0.05
            suggestions.append("Replace weak verb with strong action verb")
        else:
            suggestions.append("Start with a strong action verb")

        # Length check
        if len(bullet) > 30:
            score += 0.1
        else:
            suggestions.append("Expand with more detail")

        # Specificity bonus (contains technical terms, proper nouns)
        if re.search(r"[A-Z][a-z]+(?:\s[A-Z][a-z]+)*", bullet):
            score += 0.1

        return BulletScore(
            text=bullet,
            score=min(score, 1.0),
            has_metric=has_metric,
            has_strong_verb=has_strong_verb,
            has_weak_verb=has_weak_verb,
            suggestions=suggestions,
        )
