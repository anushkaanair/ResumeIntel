"""Quality Agent — Enforces quality standards on generated resume content.

Three-stage escalating retry loop: bullets that score below QUALITY_THRESHOLD
are retried up to MAX_RETRIES times with progressively constrained prompts.
Bullets that fail all retries are flagged as "unresolvable" in metadata.
"""

from __future__ import annotations

import re

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

QUALITY_THRESHOLD = 0.7
MAX_RETRIES = 3

# Each entry is the escalation instruction for retry attempt 0, 1, 2.
ESCALATION_PROMPTS = [
    # Retry 1 — remind about metrics
    "The previous bullet lacked quantified metrics. Rewrite with specific numbers, percentages, or timeframes.",
    # Retry 2 — tighten structure
    "The bullet still lacks impact. Use the format: [Action Verb] + [What You Did] + [Measurable Result]. Be concise.",
    # Retry 3 — most constrained
    "Final attempt. Write ONE bullet under 20 words. It must contain exactly one metric and start with a strong past-tense verb.",
]


class QualityAgent(BaseAgent):
    """Evaluates and improves resume bullet quality — verbs, metrics, impact.

    Per-bullet retry: any bullet scoring below QUALITY_THRESHOLD is re-generated
    using the LLM with escalating instructions. After MAX_RETRIES the bullet is
    preserved as-is and tagged "unresolvable" so the frontend can render a warning.
    """

    QUALITY_THRESHOLD = QUALITY_THRESHOLD
    MAX_RETRIES = MAX_RETRIES

    def __init__(self, retriever: Retriever, llm_client: object) -> None:
        self.retriever = retriever
        self.llm = llm_client

    async def execute(self, input: AgentInput) -> AgentOutput:
        # RAG: retrieve source data to verify grounding
        context = await self.retriever.retrieve(query=input.content, top_k=5)
        context_text = "\n".join(f"- {seg.content}" for seg in context)

        # First-pass analysis and bulk improvement
        analysis = self._analyze_quality(input.content)

        if analysis["needs_improvement"]:
            prompt = self._build_improvement_prompt(input, context, analysis)
            improved = await self.llm.generate(prompt)
        else:
            improved = input.content

        # Per-bullet retry for bullets still below threshold after bulk pass
        final_lines: list[str] = []
        unresolvable_bullets: list[str] = []

        for line in improved.split("\n"):
            stripped = line.strip()
            is_bullet = stripped.startswith(("-", "*", "•"))
            if not is_bullet:
                final_lines.append(line)
                continue

            bullet_score = self._score_bullet(stripped)
            if bullet_score >= QUALITY_THRESHOLD:
                final_lines.append(line)
                continue

            # Retry this bullet with escalating prompts
            retried, final_score, resolved = await self._retry_bullet(
                stripped, context_text, input
            )
            if resolved:
                # Preserve original indentation
                indent = line[: len(line) - len(line.lstrip())]
                final_lines.append(indent + retried)
            else:
                # Keep the best attempt; flag for the frontend
                indent = line[: len(line) - len(line.lstrip())]
                final_lines.append(indent + retried)
                unresolvable_bullets.append(retried)
                logger.warning(
                    "quality_agent.unresolvable_bullet",
                    bullet=stripped[:80],
                    final_score=round(final_score, 3),
                )

        final_content = "\n".join(final_lines)
        overall_score = self._calculate_score(final_content)

        return AgentOutput(
            content=final_content,
            quality_score=overall_score,
            sources=context,
            suggestions=analysis["suggestions"],
            metadata={
                "weak_verbs_found": analysis["weak_verb_count"],
                "bullets_without_metrics": analysis["no_metric_count"],
                "improved": analysis["needs_improvement"],
                "unresolvable_bullets": unresolvable_bullets,
                "unresolvable_count": len(unresolvable_bullets),
            },
            provenance=Provenance(
                agent_name="quality",
                input_summary=final_content[:200],
                retrieved_chunks=[seg.segment_id for seg in context],
                decision_rationale=(
                    f"Enforced quality gate: fixed {analysis['weak_verb_count']} weak verbs, "
                    f"improved {analysis['no_metric_count']} metric-missing bullets. "
                    f"{len(unresolvable_bullets)} bullets marked unresolvable after 3 retries."
                ),
                confidence=overall_score,
            ),
        )

    def validate_input(self, input: AgentInput) -> None:
        if not input.content:
            raise ValueError("No content to evaluate quality")

    def validate_output(self, output: AgentOutput) -> None:
        if output.quality_score < self.QUALITY_THRESHOLD:
            raise QualityGateError(
                f"Quality score {output.quality_score:.2f} below threshold {self.QUALITY_THRESHOLD}"
            )

    # ------------------------------------------------------------------
    # Per-bullet retry
    # ------------------------------------------------------------------

    async def _retry_bullet(
        self, bullet: str, context_text: str, input: AgentInput
    ) -> tuple[str, float, bool]:
        """Retry a single bullet up to MAX_RETRIES times with escalating prompts.

        Returns:
            (final_bullet, final_score, resolved)
            resolved=False means all retries failed — caller should flag as unresolvable.
        """
        current = bullet
        score = self._score_bullet(current)

        for attempt in range(MAX_RETRIES):
            escalation = ESCALATION_PROMPTS[attempt]
            prompt = (
                f"You are a resume quality specialist. Rewrite the following resume bullet.\n\n"
                f"INSTRUCTION: {escalation}\n\n"
                f"CURRENT BULLET:\n{current}\n\n"
                f"SOURCE DATA (only use numbers/facts that appear here):\n{context_text}\n\n"
                f"Rules:\n"
                f"- Start with a strong past-tense action verb\n"
                f"- Include at least one metric if supported by source data\n"
                f"- Do NOT fabricate numbers\n"
                f"- Return ONLY the rewritten bullet, no explanation\n"
            )
            rewritten = await self.llm.generate(prompt)
            # Strip any leading bullet marker the LLM may add, then normalize
            rewritten = rewritten.strip().lstrip("-*• ").strip()
            # Re-prefix with the original marker style
            marker = bullet[0] if bullet[0] in ("-", "*", "•") else "-"
            rewritten = f"{marker} {rewritten}"

            score = self._score_bullet(rewritten)
            logger.debug(
                "quality_agent.retry_bullet",
                attempt=attempt + 1,
                score=round(score, 3),
            )
            current = rewritten
            if score >= QUALITY_THRESHOLD:
                return current, score, True

        return current, score, False

    def _score_bullet(self, bullet: str) -> float:
        """Score a single bullet on [0, 1]."""
        has_strong_verb = any(v in bullet.lower() for v in STRONG_VERBS)
        has_metric = bool(re.search(r"\d+", bullet))
        has_weak_verb = any(v in bullet.lower() for v in WEAK_VERBS)

        base = 0.3
        if has_strong_verb:
            base += 0.35
        if has_metric:
            base += 0.35
        if has_weak_verb:
            base -= 0.15
        return max(0.0, min(base, 1.0))

    # ------------------------------------------------------------------
    # Bulk-pass helpers (unchanged logic)
    # ------------------------------------------------------------------

    def _analyze_quality(self, content: str) -> dict:
        bullets = [
            line.strip()
            for line in content.split("\n")
            if line.strip().startswith(("-", "*", "•"))
        ]

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
        needs_improvement = (
            weak_verb_count / total > 0.3 or no_metric_count / total > 0.5
        )

        return {
            "weak_verb_count": weak_verb_count,
            "no_metric_count": no_metric_count,
            "suggestions": suggestions,
            "needs_improvement": needs_improvement,
            "total_bullets": len(bullets),
        }

    def _build_improvement_prompt(self, input: AgentInput, context: list, analysis: dict) -> str:
        context_text = "\n".join(f"- {seg.content}" for seg in context)

        return f"""You are a senior resume quality reviewer with expertise in ATS optimization and technical hiring.
Your job is to fix specific quality issues in resume bullets without changing the meaning or fabricating anything.

QUALITY ISSUES IDENTIFIED:
- Bullets with weak verbs: {analysis['weak_verb_count']}
- Bullets missing quantifiable metrics: {analysis['no_metric_count']}

IMPROVEMENT RULES — STRICTLY ENFORCE:
1. WEAK VERBS → Replace with strong action verbs ONLY:
   - "worked on" → "Built" | "helped" → "Contributed to" | "was responsible for" → "Owned"
   - "handled" → "Managed" | "assisted" → "Supported" | "participated in" → "Delivered"
   - Preferred verbs: Led, Designed, Implemented, Built, Architected, Optimized, Automated, Reduced, Increased, Launched, Migrated, Scaled, Delivered, Orchestrated
2. MISSING METRICS → Add numbers ONLY if they appear in the source data below. Do NOT estimate or round up.
   - If no number exists in source, rephrase to emphasize scope/impact without fabricating a figure.
3. TRUTHFULNESS → Do not change who the candidate is, what they built, or what results they achieved.
4. PRESERVE FORMAT → Return ALL bullets including unchanged ones. Do not drop any bullet.
5. COMPLETENESS → Keep all section headings exactly as they appear in the input.

RESUME CONTENT TO IMPROVE:
{input.content}

SOURCE DATA (ground truth — only add metrics that appear here):
{context_text}

Return the complete improved resume in the same markdown format as the input. Every section and bullet must appear in the output."""

    def _calculate_score(self, content: str) -> float:
        bullets = [
            line.strip()
            for line in content.split("\n")
            if line.strip().startswith(("-", "*", "•"))
        ]
        if not bullets:
            return 0.5

        total = len(bullets)
        strong_count = sum(
            1 for b in bullets if any(v in b.lower() for v in STRONG_VERBS)
        )
        metric_count = sum(1 for b in bullets if re.search(r"\d+", b))

        verb_score = strong_count / total
        metric_score = metric_count / total

        return 0.3 + (verb_score * 0.35) + (metric_score * 0.35)
