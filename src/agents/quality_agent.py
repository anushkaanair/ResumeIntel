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
        self.validate_input(input)

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

        output = AgentOutput(
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
        self.validate_output(output)
        return output

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

        return f"""You are an expert resume quality reviewer. Improve the following resume content.

ISSUES FOUND:
- Weak verbs: {analysis['weak_verb_count']} bullets
- Missing metrics: {analysis['no_metric_count']} bullets

RULES:
- Replace weak verbs with strong action verbs (Led, Designed, Implemented, Optimized)
- Add quantifiable metrics where possible, but ONLY from source data
- Never fabricate achievements or numbers
- Maintain truthfulness — enhance presentation, not content

CURRENT CONTENT:
{input.content}

SOURCE DATA FOR VERIFICATION:
{context_text}

Return improved bullets in the same format."""

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
