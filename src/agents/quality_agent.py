"""Quality Agent — Enforces quality standards on generated resume content."""

from __future__ import annotations

import re

import structlog

from src.agents.base_agent import AgentInput, AgentOutput, BaseAgent
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


class QualityAgent(BaseAgent):
    """Evaluates and improves resume bullet quality — verbs, metrics, impact."""

    QUALITY_THRESHOLD = 0.7
    MAX_RETRIES = 3

    def __init__(self, retriever: Retriever, llm_client: object) -> None:
        self.retriever = retriever
        self.llm = llm_client

    async def execute(self, input: AgentInput) -> AgentOutput:
        # RAG: retrieve source data to verify grounding
        context = await self.retriever.retrieve(query=input.content, top_k=5)

        # Analyze current quality
        analysis = self._analyze_quality(input.content)

        if analysis["needs_improvement"]:
            prompt = self._build_improvement_prompt(input, context, analysis)
            improved = await self.llm.generate(prompt)
        else:
            improved = input.content

        quality_score = self._calculate_score(improved)

        return AgentOutput(
            content=improved,
            quality_score=quality_score,
            sources=context,
            suggestions=analysis["suggestions"],
            metadata={
                "weak_verbs_found": analysis["weak_verb_count"],
                "bullets_without_metrics": analysis["no_metric_count"],
                "improved": analysis["needs_improvement"],
            },
        )

    def validate_input(self, input: AgentInput) -> None:
        if not input.content:
            raise ValueError("No content to evaluate quality")

    def validate_output(self, output: AgentOutput) -> None:
        if output.quality_score < self.QUALITY_THRESHOLD:
            raise QualityGateError(
                f"Quality score {output.quality_score:.2f} below threshold {self.QUALITY_THRESHOLD}"
            )

    def _analyze_quality(self, content: str) -> dict:
        """Analyze content for quality issues."""
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
            # Check for weak verbs
            if any(verb in lower for verb in WEAK_VERBS):
                weak_verb_count += 1
                suggestions.append(f"Replace weak verb in: {bullet[:60]}...")

            # Check for metrics
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
        """Calculate quality score for content."""
        bullets = [
            line.strip()
            for line in content.split("\n")
            if line.strip().startswith(("-", "*", "•"))
        ]
        if not bullets:
            return 0.5  # Non-bullet content gets a base score

        total = len(bullets)
        strong_count = sum(
            1 for b in bullets if any(v in b.lower() for v in STRONG_VERBS)
        )
        metric_count = sum(1 for b in bullets if re.search(r"\d+", b))

        verb_score = strong_count / total
        metric_score = metric_count / total

        return 0.3 + (verb_score * 0.35) + (metric_score * 0.35)
