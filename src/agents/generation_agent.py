"""Generation Agent — Generates optimized resume bullets using RAG-grounded LLM."""

from __future__ import annotations

import structlog

from src.agents.base_agent import AgentInput, AgentOutput, BaseAgent, Provenance
from src.exceptions import QualityGateError
from src.rag.retriever import Retriever
from src.scoring.grounding import check, retry_feedback

logger = structlog.get_logger()


class GenerationAgent(BaseAgent):
    """Generates optimized, ATS-friendly resume bullets grounded in source data."""

    QUALITY_THRESHOLD = 0.7
    MAX_RETRIES = 3

    def __init__(self, retriever: Retriever, llm_client: object) -> None:
        self.retriever = retriever
        self.llm = llm_client
        # Set when an attempt is rejected; injected into the next attempt's prompt.
        self._feedback = ""

    async def execute(self, input: AgentInput) -> AgentOutput:
        # RAG: retrieve relevant context from indexed resume segments
        context = await self.retriever.retrieve(
            query=input.job_description or input.content,
            top_k=10,
        )

        prompt = self._build_prompt(input, context)
        result = await self.llm.generate(prompt)
        score = self._score_output(result, context)

        # Grounding: did the rewrite make claims the source resume never made?
        source = input.metadata.get("source_text") or input.content
        report = check(result, [source], input.job_description)
        grounded = not report.flagged
        self._feedback = retry_feedback(report)

        provenance = Provenance(
            agent_name="GenerationAgent",
            input_summary=input.content[:200],
            retrieved_chunk_ids=[seg.segment_id for seg in context],
            decision_rationale=(
                f"Rewrote bullets using {len(context)} retrieved segment(s). "
                + (
                    "Grounding check passed: no new numbers or skills versus the source resume."
                    if grounded
                    else "Grounding check FAILED: output added "
                    f"numbers {report.novel_numbers[:6]} and JD skills {report.injected_jd_terms[:6]} "
                    "that the source resume does not contain."
                )
            ),
            confidence=score,
        )

        return AgentOutput(
            content=result,
            quality_score=score,
            sources=context,
            provenance=provenance,
            metadata={"grounded": grounded, "grounding": report.as_dict(), "source_count": len(context)},
        )

    def validate_input(self, input: AgentInput) -> None:
        if not input.content:
            raise ValueError("Empty resume content")
        if not input.sections and not input.previous_output:
            raise ValueError("No parsed sections available — run IngestionAgent first")

    def validate_output(self, output: AgentOutput) -> None:
        if output.quality_score < self.QUALITY_THRESHOLD:
            raise QualityGateError(
                f"Generation quality {output.quality_score:.2f} below threshold"
            )
        if not output.sources:
            raise QualityGateError("Output not grounded in any source data")
        if not output.metadata.get("grounded", True):
            g = output.metadata.get("grounding", {})
            raise QualityGateError(
                "Rewrite added claims absent from the source resume "
                f"(numbers {g.get('novel_numbers', [])[:6]}, skills {g.get('injected_jd_terms', [])[:6]})"
            )

    def _build_prompt(self, input: AgentInput, context: list) -> str:
        context_text = "\n".join(
            f"- {seg.content} (relevance: {seg.score:.2f})" for seg in context
        )

        sections = input.sections or (
            input.previous_output.sections if input.previous_output else {}
        )
        sections_text = "\n".join(
            f"### {name}\n{content}" for name, content in sections.items()
        )

        return f"""You are an expert resume writer specializing in ATS optimization for competitive tech roles.
Your task is to rewrite resume bullets to maximize impact, clarity, and ATS keyword alignment.

STRICT RULES — MUST FOLLOW:
1. GROUNDING: Every bullet must trace directly to the source data. Do not invent projects, metrics, tools, or achievements.
2. ACTION VERBS: Start every bullet with a strong action verb — past tense for past roles, present tense for the current ("Present") role.
3. METRICS: Use a number ONLY if that exact number appears in the source data. If the source has no metric for a bullet, write it without one. Never estimate, round up or invent a figure.
4. KEYWORDS: Reuse the job description's wording ONLY for skills the source already shows. Never add a technology, skill or responsibility the source does not mention, even if the job description asks for it.
5. LENGTH: Each bullet should be 1–2 lines. No sub-bullets. No generic filler phrases like "responsible for" or "worked on".
6. COMPLETENESS: Output ALL sections present in the source — do not drop any section.
7. HEADER: Preserve the candidate name, contact info, and title exactly as given — do not modify.

{self._feedback}
SOURCE RESUME DATA (authoritative — do not contradict):
{sections_text}

RETRIEVED CONTEXT (high-relevance segments from RAG — use these for grounding):
{context_text}

TARGET JOB DESCRIPTION:
{input.job_description or "General optimization — improve impact and clarity for software engineering roles"}

OUTPUT FORMAT:
Return the full resume with each section as a markdown heading (## Section Name) followed by bullet points (- bullet text).
Example:
## Experience
- Led migration of legacy monolith to microservices, reducing p99 latency by 40%

## Skills
Python, FastAPI, PostgreSQL, Docker, AWS"""

    def _score_output(self, result: str, context: list) -> float:
        """Structural sanity only (non-empty, has bullets, grounded in retrieved context).

        This deliberately does not reward numbers or keywords: whether the content
        is *honest* is decided by the grounding check, not by how impressive it looks.
        """
        if not result.strip():
            return 0.0
        score = 0.5
        lines = result.strip().split("\n")
        if any(l.strip().startswith(("-", "*", "•")) for l in lines):
            score += 0.2
        if any(l.lstrip().startswith("#") for l in lines):
            score += 0.15
        if context:
            score += 0.15
        return min(score, 1.0)
