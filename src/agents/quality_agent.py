"""Quality Agent — per-bullet quality gate with 3-stage escalating constraint retry.

A bullet is scored on what makes it good *without* requiring it to be invented:

* a strong action verb opens it,
* it is specific — it carries a number that exists in the source, or at least two
  concrete technologies that exist in the source,
* it is concise.

A bullet below the threshold is rewritten up to three times with progressively
tighter constraints. A rewrite is rejected outright if it adds a number or a
skill the source resume never mentioned, so the gate cannot be passed by making
something up. A bullet that cannot be improved honestly is kept as written and
flagged ``unresolvable`` — the user sees it rather than a fabricated upgrade.
"""

from __future__ import annotations

import re
from typing import Any

import structlog

from src.agents.base_agent import AgentInput, AgentOutput, BaseAgent, Provenance
from src.exceptions import QualityGateError
from src.rag.retriever import Retriever
from src.scoring.grounding import check, numbers_in, retry_feedback
from src.scoring.keywords import terms_in

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

# Action verbs that do not end in "-ed", plus present-tense forms for current roles.
_IRREGULAR_VERBS = {
    "built", "led", "wrote", "ran", "shipped", "drove", "made", "grew", "cut", "won", "taught",
    "build", "lead", "design", "implement", "develop", "maintain", "own", "ship", "write",
    "integrate", "diagnose", "test", "deliver", "architect", "automate", "optimize", "create",
    "engineer", "manage", "mentor", "analyze", "research", "train", "evaluate", "deploy",
    "run", "drive", "support", "contribute", "collaborate", "improve", "reduce", "scale",
}

# Three escalating constraint prompts (README novel step 3). None of them asks for
# a number the source does not contain.
ESCALATING_STAGE_INSTRUCTIONS = [
    "Rewrite with a stronger action verb and the most concrete technical detail from the source. "
    "Use a number only if it appears in the source; if it has none, add none.",
    "Use the format [Action Verb] + [What You Did] + [Result, only if the source states one]. Be concise. "
    "Do not add any technology, tool or figure that is not in the source.",
    "Write ONE bullet under 20 words. Start with a strong action verb. Include at most one number, and only "
    "if that exact number is in the source. Name the specific technologies the source mentions.",
]

_MARKER = re.compile(r"^(\s*[-*•]\s*)")


def _first_word(text: str) -> str:
    m = re.match(r"\W*([A-Za-z]+)", text)
    return m.group(1).lower() if m else ""


class QualityAgent(BaseAgent):
    """Evaluates and improves resume bullet quality with 3-stage escalating retry."""

    # Per-bullet gate. The agent-level score is a mean for reporting; it is not a
    # pass/fail threshold, because an honest resume legitimately has bullets that
    # cannot be improved without inventing something.
    QUALITY_THRESHOLD = 0.7
    MAX_RETRIES = 2
    BULLET_THRESHOLD = 0.7

    def __init__(self, retriever: Retriever, llm_client: object) -> None:
        self.retriever = retriever
        self.llm = llm_client
        self._source = ""
        self._jd = ""
        self._source_numbers: set[str] = set()
        self._source_terms: set[str] = set()

    async def execute(self, input: AgentInput) -> AgentOutput:
        context = await self.retriever.retrieve(query=input.content, top_k=5)
        chunk_ids = [seg.segment_id for seg in context]
        context_text = "\n".join(f"- {seg.content}" for seg in context)

        # What counts as "in the source": the user's original resume, not the
        # previous agent's rewrite.
        self._source = input.metadata.get("source_text") or input.content
        self._jd = input.job_description
        self._source_numbers = numbers_in(self._source)
        self._source_terms = terms_in(self._source, specific_only=True)

        bullets = self._extract_bullets(input.content)
        improved_bullets: list[str] = []
        unresolvable: list[dict[str, Any]] = []
        improved_count = 0

        for bullet in bullets:
            result, last_score = await self._optimize_bullet(bullet, context_text)
            if result is None:
                unresolvable.append({
                    "original_text": bullet,
                    "last_score": round(last_score, 3),
                    "status": "unresolvable",
                })
                improved_bullets.append(bullet)  # keep this step's input unchanged rather than invent an upgrade
            else:
                if result != bullet:
                    improved_count += 1
                improved_bullets.append(result)

        improved_content = self._reassemble(input.content, bullets, improved_bullets)
        overall_score = self._calculate_score(improved_content)
        analysis = self._analyze_quality(input.content)

        provenance = Provenance(
            agent_name="QualityAgent",
            input_summary=input.content[:200],
            retrieved_chunk_ids=chunk_ids,
            decision_rationale=(
                f"Scored {len(bullets)} bullets: {improved_count} rewritten, "
                f"{len(unresolvable)} could not be improved without adding claims that are not in "
                "your resume (left as they were after the previous step)."
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
                "improved": improved_count > 0,
                "improved_count": improved_count,
                "weak_verbs_found": analysis["weak_verb_count"],
                "bullets_without_metrics": analysis["no_metric_count"],
                "unresolvable_count": len(unresolvable),
                "total_bullets": len(bullets),
            },
        )

    async def _optimize_bullet(self, bullet: str, context_text: str) -> tuple[str | None, float]:
        """Run up to 3 escalating constraint stages on a single bullet.

        Returns (final_text, score), or (None, last_score) if every stage failed.
        """
        score = self._score_bullet(bullet)
        if score >= self.BULLET_THRESHOLD:
            return bullet, score

        m = _MARKER.match(bullet)
        marker = m.group(1) if m else "- "
        current = bullet
        last_score = score
        feedback = ""
        for stage_idx, instruction in enumerate(ESCALATING_STAGE_INSTRUCTIONS):
            prompt = self._build_stage_prompt(current, context_text, stage_idx, instruction, feedback)
            rewritten = await self.llm.generate(prompt)
            text = self._extract_first_bullet(rewritten)
            if not text:
                lines = rewritten.strip().splitlines()
                text = lines[0].lstrip("-•* ").strip() if lines else ""
            candidate = f"{marker}{text}" if text else ""

            report = (
                check(candidate, [self._source], self._jd, number_sources=[bullet]) if candidate else None
            )
            if report is not None and report.flagged:
                # Passing the gate by inventing something (or by borrowing another bullet's figure) is not passing.
                feedback = retry_feedback(report)
                logger.debug("quality.rewrite_rejected", stage=stage_idx + 1, novel=report.novel_numbers,
                             injected=report.injected_jd_terms)
                continue

            new_score = self._score_bullet(candidate) if candidate else 0.0
            logger.debug("quality.retry_stage", stage=stage_idx + 1, score_before=last_score, score_after=new_score)
            if new_score >= self.BULLET_THRESHOLD:
                return candidate, new_score
            if new_score > last_score:
                current, last_score = candidate, new_score
            feedback = ""

        return None, last_score

    def _build_stage_prompt(self, bullet: str, context_text: str, stage: int, instruction: str, feedback: str = "") -> str:
        return f"""You are a senior resume editor. Apply this specific instruction to rewrite the bullet below.

INSTRUCTION (Stage {stage + 1}/3): {instruction}
{feedback}
CURRENT BULLET:
{bullet}

SOURCE DATA (the ONLY facts you may use — never add a number, tool or achievement that is not here):
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
        if not output.content.strip():
            raise QualityGateError("Quality agent produced empty content")
        # Backstop: every accepted rewrite was already checked, so the assembled
        # content must not contain claims beyond the source.
        if self._source:
            report = check(output.content, [self._source], self._jd)
            if report.flagged:
                raise QualityGateError(
                    f"Output contains claims absent from the source (numbers {report.novel_numbers[:6]}, "
                    f"skills {report.injected_jd_terms[:6]})"
                )

    def _extract_bullets(self, content: str) -> list[str]:
        return [
            line.rstrip()
            for line in content.split("\n")
            if line.strip().startswith(("-", "*", "•"))
        ]

    def _reassemble(self, original: str, old_bullets: list[str], new_bullets: list[str]) -> str:
        """Replace old bullet lines with improved versions, line by line (order-safe)."""
        replacements = list(zip(old_bullets, new_bullets))
        out, i = [], 0
        for line in original.split("\n"):
            if i < len(replacements) and line.rstrip() == replacements[i][0]:
                out.append(replacements[i][1])
                i += 1
            else:
                out.append(line)
        return "\n".join(out)

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
                suggestions.append(
                    f"No figure in: {bullet[:60]}... (add one only if you have a real number for it)"
                )

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
        """Score one bullet 0..0.9 on verb, specificity and concision.

        Specificity is satisfied by a number or by two concrete technologies that
        are *in the source* — so an honest, technical bullet with no metric can
        still pass, and an invented number earns nothing.
        """
        text = _MARKER.sub("", bullet)
        lower = text.lower()
        first = _first_word(text)
        has_strong_verb = (
            (first in STRONG_VERBS or first in _IRREGULAR_VERBS or first.endswith("ed"))
            and first not in {"worked", "helped", "assisted", "participated", "handled", "tasked", "involved"}
        )
        nums = numbers_in(text)
        sources = self._source_numbers if self._source else nums
        has_real_number = bool(nums & sources)
        techs = terms_in(text, specific_only=True)
        tech_ok = len(techs & self._source_terms) >= 2 if self._source else len(techs) >= 2
        concise = len(text.split()) <= 30
        weak = any(v in lower for v in WEAK_VERBS)

        score = (0.4 if has_strong_verb else 0.0) + (0.3 if (has_real_number or tech_ok) else 0.0) + (0.2 if concise else 0.0)
        if weak:
            score -= 0.2
        return round(max(score, 0.0), 3)

    def _calculate_score(self, content: str) -> float:
        bullets = self._extract_bullets(content)
        if not bullets:
            return 0.5
        scores = [self._score_bullet(b) for b in bullets]
        return sum(scores) / len(scores)
