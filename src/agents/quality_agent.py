"""Quality Agent — Enforces quality standards with 3-stage escalating constraint retry."""

from __future__ import annotations

import re
from typing import Any

import structlog

from src.agents.base_agent import AgentInput, AgentOutput, BaseAgent, Provenance
from src.exceptions import QualityGateError
from src.rag.retriever import Retriever

logger = structlog.get_logger()

WEAK_VERBS = {
    "worked", "helped", "assisted", "participated", "was responsible",
    "handled", "dealt with", "involved in", "tasked with",
}

STRONG_VERBS = {
    "led", "designed", "implemented", "optimized", "delivered", "built",
    "architected", "automated", "reduced", "increased", "achieved",
    "launched", "migrated", "scaled", "streamlined", "orchestrated",
}

# Three escalating constraint prompts per patent claim 3
ESCALATING_STAGE_INSTRUCTIONS = [
    "The previous bullet lacked quantified metrics. Rewrite with specific numbers, percentages, or timeframes.",
    "Use format: [Action Verb] + [What You Did] + [Measurable Result]. Be concise.",
    "Write ONE bullet under 20 words. Must contain exactly one metric. Start with a strong past-tense verb.",
]


class QualityAgent(BaseAgent):
    """Evaluates and improves resume bullet quality with 3-stage escalating retry."""

    QUALITY_THRESHOLD = 0.7
    MAX_RETRIES = 3  # used by base class for overall pipeline retries
    BULLET_THRESHOLD = 0.7  # per-bullet threshold

    def __init__(self, retriever: Retriever, llm_client: object) -> None:
        self.retriever = retriever
        self.llm = llm_client

    async def execute(self, input: AgentInput) -> AgentOutput:
        context = await self.retriever.retrieve(query=input.content, top_k=5)
        chunk_ids = [seg.segment_id for seg in context]
        context_text = "\n".join(f"- {seg.content}" for seg in context)

        bullets = self._extract_bullets(input.content)
        improved_bullets: list[str] = []
        unresolvable: list[dict[str, Any]] = []

        for bullet in bullets:
            result, last_score = await self._optimize_bullet(bullet, context_text)
            if result is None:
                # All 3 stages failed — flag as unresolvable
                unresolvable.append({
                    "original_text": bullet,
                    "last_score": last_score,
                    "status": "unresolvable",
                })
                improved_bullets.append(bullet)  # keep original in output
            else:
                improved_bullets.append(result)

        # Reassemble full content replacing bullet lines
        improved_content = self._reassemble(input.content, bullets, improved_bullets)
        overall_score = self._calculate_score(improved_content)

        analysis = self._analyze_quality(input.content)

        provenance = Provenance(
            agent_name="QualityAgent",
            input_summary=input.content[:200],
            retrieved_chunk_ids=chunk_ids,
            decision_rationale=(
                f"Processed {len(bullets)} bullets. "
                f"{len(unresolvable)} unresolvable after 3 escalating retry stages."
            ),
            confidence=overall_score,
        )

        return AgentOutput(
            content=improved_content,
            quality_score=overall_score,
            sources=context,
            suggestions=analysis["suggestions"],
            unresolvable_bullets=unresolvable,
            provenance=provenance,
            metadata={
                "weak_verbs_found": analysis["weak_verb_count"],
                "bullets_without_metrics": analysis["no_metric_count"],
                "unresolvable_count": len(unresolvable),
                "total_bullets": len(bullets),
            },
        )

    async def _optimize_bullet(self, bullet: str, context_text: str) -> tuple[str | None, float]:
        """Run up to 3 escalating constraint stages on a single bullet.

        Returns (improved_text, score) or (None, last_score) if all stages fail.
        """
        score = self._score_bullet(bullet)
        if score >= self.BULLET_THRESHOLD:
            return bullet, score

        current = bullet
        last_score = score
        for stage_idx, instruction in enumerate(ESCALATING_STAGE_INSTRUCTIONS):
            prompt = self._build_stage_prompt(current, context_text, stage_idx, instruction)
            rewritten = await self.llm.generate(prompt)
            # Take first non-empty line that looks like a bullet
            candidate = self._extract_first_bullet(rewritten) or rewritten.strip()
            new_score = self._score_bullet(candidate)
            logger.debug(
                "quality.retry_stage",
                stage=stage_idx + 1,
                score_before=last_score,
                score_after=new_score,
            )
            if new_score >= self.BULLET_THRESHOLD:
                return candidate, new_score
            current = candidate
            last_score = new_score

        return None, last_score

    def _build_stage_prompt(self, bullet: str, context_text: str, stage: int, instruction: str) -> str:
        return f"""You are a senior resume editor. Apply this specific instruction to rewrite the bullet below.

INSTRUCTION (Stage {stage + 1}/3): {instruction}

CURRENT BULLET:
{bullet}

SOURCE DATA (do NOT fabricate anything not present here):
{context_text}

Return ONLY the single rewritten bullet line. No explanation. No prefix."""

    def _extract_first_bullet(self, text: str) -> str:
        for line in text.strip().splitlines():
            line = line.strip()
            if line and (line[0] in "-•*" or line[0].isupper()):
                return line.lstrip("-•* ")
        return ""

    def validate_input(self, input: AgentInput) -> None:
        if not input.content:
            raise ValueError("No content to evaluate quality")

    def validate_output(self, output: AgentOutput) -> None:
        if output.quality_score < self.QUALITY_THRESHOLD:
            raise QualityGateError(
                f"Quality score {output.quality_score:.2f} below threshold {self.QUALITY_THRESHOLD}"
            )

    def _extract_bullets(self, content: str) -> list[str]:
        return [
            line.strip()
            for line in content.split("\n")
            if line.strip().startswith(("-", "*", "•"))
        ]

    def _reassemble(self, original: str, old_bullets: list[str], new_bullets: list[str]) -> str:
        """Replace old bullet lines in original content with improved versions."""
        result = original
        for old, new in zip(old_bullets, new_bullets):
            result = result.replace(old, new, 1)
        return result

    def _analyze_quality(self, content: str) -> dict:
        bullets = self._extract_bullets(content)
        weak_verb_count = 0
        no_metric_count = 0
        suggestions: list[str] = []

        for bullet in bullets:
            lower = bullet.lower()
            if any(verb in lower for verb in WEAK_VERBS):
                weak_verb_count += 1
                suggestions.append(f"Replace weak verb in: {bullet[:60]}...")
            if not re.search(r"\d+", bullet):
                no_metric_count += 1
                suggestions.append(f"Add metrics to: {bullet[:60]}...")

        total = max(len(bullets), 1)
        needs_improvement = weak_verb_count / total > 0.3 or no_metric_count / total > 0.5

        return {
            "weak_verb_count": weak_verb_count,
            "no_metric_count": no_metric_count,
            "suggestions": suggestions,
            "needs_improvement": needs_improvement,
            "total_bullets": len(bullets),
        }

    def _score_bullet(self, bullet: str) -> float:
        """Score a single bullet on strong verb + metric presence."""
        lower = bullet.lower()
        has_strong_verb = any(v in lower for v in STRONG_VERBS)
        has_metric = bool(re.search(r"\d+", bullet))
        return 0.3 + (0.35 if has_strong_verb else 0.0) + (0.35 if has_metric else 0.0)

    def _calculate_score(self, content: str) -> float:
        bullets = self._extract_bullets(content)
        if not bullets:
            return 0.5
        scores = [self._score_bullet(b) for b in bullets]
        return sum(scores) / len(scores)
