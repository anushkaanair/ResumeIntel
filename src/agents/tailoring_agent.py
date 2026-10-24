"""Tailoring Agent — tailors a resume to a JD behind a semantic alignment gate.

Two safeguards:

* **Alignment gate** (README novel step 2): if the resume and JD embeddings are
  too far apart, tailoring stops and returns a ranked diagnosis of which
  *editable* sections are weakest and which JD skills are missing, instead of
  forcing a rewrite of a resume that does not fit the role.
* **Grounding**: the tailored text may reorder, emphasise and reword, but it may
  not add a number or a skill the resume never contained. A rewrite that does is
  rejected and retried with the offending items named.
"""

from __future__ import annotations

import re

import numpy as np
import structlog

from src.agents.base_agent import AgentInput, AgentOutput, BaseAgent, Provenance
from src.config.settings import settings
from src.exceptions import NonRetryableError, QualityGateError
from src.rag.retriever import Retriever
from src.scoring.grounding import check, retry_feedback
from src.scoring.keywords import extract_jd_keywords, missing_keywords, terms_in

logger = structlog.get_logger()

# Cosine similarity between resume and JD embeddings below which tailoring stops.
# Calibrated on real postings — see Settings.alignment_threshold.
ALIGNMENT_THRESHOLD = settings.alignment_threshold

# Sections a user can actually act on when told "this section is weak".
# Education, languages and the contact header will always look "unrelated" to a
# JD; ranking them as the weakest sections is noise, not advice.
_EDITABLE_SECTIONS = {
    "experience", "work experience", "professional experience", "internships",
    "projects", "personal projects", "selected projects",
    "skills", "technical skills", "core competencies", "technologies", "tech stack",
    "summary", "professional summary", "about", "about me", "profile", "objective",
}


class AlignmentGateError(NonRetryableError):
    """Raised when resume-JD cosine similarity is below the gate threshold."""

    def __init__(
        self,
        alignment_score: float,
        weak_sections: list[dict],
        missing_skills: list[str] | None = None,
    ) -> None:
        self.alignment_score = alignment_score
        self.weak_sections = weak_sections  # ranked list of {section, score}
        self.missing_skills = missing_skills or []
        super().__init__(
            f"Alignment score {alignment_score:.3f} below threshold {ALIGNMENT_THRESHOLD}. "
            f"Weakest editable sections: {[s['section'] for s in weak_sections]}"
        )


class TailoringAgent(BaseAgent):
    """Tailors a resume to a job description without adding claims."""

    QUALITY_THRESHOLD = 0.7
    MAX_RETRIES = 3

    def __init__(self, retriever: Retriever, llm_client: object) -> None:
        self.retriever = retriever
        self.llm = llm_client
        self._feedback = ""
        self._alignment_cache: dict[tuple[str, str], tuple[float, list[dict], np.ndarray]] = {}

    async def execute(self, input: AgentInput) -> AgentOutput:
        # ── Semantic alignment gate ──────────────────────────────────────────
        alignment_score, weak_sections, jd_vec = await self._check_alignment(input)
        if alignment_score < ALIGNMENT_THRESHOLD:
            logger.warning(
                "tailoring.alignment_gate_abort",
                score=alignment_score,
                weak_sections=[s["section"] for s in weak_sections],
            )
            raise AlignmentGateError(
                alignment_score,
                weak_sections,
                [k.term for k in missing_keywords(input.content, input.job_description, limit=8)],
            )

        # ── Normal tailoring path ────────────────────────────────────────────
        context = await self.retriever.retrieve(query=input.job_description, top_k=10)
        chunk_ids = [seg.segment_id for seg in context]

        weaknesses = input.previous_output.suggestions if input.previous_output else []

        prompt = self._build_prompt(input, context, weaknesses)
        tailored = await self.llm.generate(prompt)

        source = input.metadata.get("source_text") or input.content
        tailored = self._drop_invented_title(tailored, source)
        report = check(tailored, [source], input.job_description)
        grounded = not report.flagged
        self._feedback = retry_feedback(report)
        structure_ok, structure_note = self._structure_preserved(input.content, tailored)

        embedder = self.retriever.embedder
        post_alignment = float(np.dot(embedder.encode_single(tailored), jd_vec))
        cov_before = self._coverage(input.content, input.job_description)
        cov_after = self._coverage(tailored, input.job_description)

        final_score = 1.0 if (grounded and structure_ok) else 0.4

        provenance = Provenance(
            agent_name="TailoringAgent",
            input_summary=input.content[:200],
            retrieved_chunk_ids=chunk_ids,
            decision_rationale=(
                f"Semantic alignment {alignment_score:.3f} -> {post_alignment:.3f}; "
                f"JD skill coverage {cov_before:.0%} -> {cov_after:.0%}. "
                + ("No new numbers or skills added." if grounded else
                   f"REJECTED: added numbers {report.novel_numbers[:6]} / skills {report.injected_jd_terms[:6]}. ")
                + ("" if structure_ok else f" Structure problem: {structure_note}.")
            ),
            confidence=final_score,
        )

        return AgentOutput(
            content=tailored,
            quality_score=final_score,
            sources=context,
            provenance=provenance,
            metadata={
                "alignment_score": post_alignment,
                "pre_tailoring_alignment": alignment_score,
                "weaknesses_addressed": len(weaknesses),
                "keyword_coverage_before": round(cov_before, 3),
                "keyword_coverage_after": round(cov_after, 3),
                "grounded": grounded,
                "grounding": report.as_dict(),
                "structure_ok": structure_ok,
                "structure_note": structure_note,
            },
        )

    async def _check_alignment(self, input: AgentInput) -> tuple[float, list[dict], np.ndarray]:
        """Cosine similarity between full resume and JD embeddings.

        Returns (overall_score, ranked_weak_editable_sections, jd_vector).
        Note the embedding model reads only the first ~256 tokens of each text;
        the score reflects the opening of each document. That is adequate for
        telling a related role from an unrelated one (see calibration), not for
        fine-grained ranking of two similar roles.
        """
        key = (input.metadata.get("source_text") or input.content, input.job_description)
        if key in self._alignment_cache:  # BaseAgent retries execute(); the inputs have not changed
            return self._alignment_cache[key]
        embedder = self.retriever.embedder

        # Calibrated on the full original resume; the previous agent's output is a trimmed
        # rewrite (no header/education) and scores systematically lower against the same JD.
        resume_vec = embedder.encode_single(input.metadata.get("source_text") or input.content)
        jd_vec = embedder.encode_single(input.job_description)
        overall_score = float(np.dot(resume_vec, jd_vec))  # vectors are L2-normalised

        candidates = {
            name: text for name, text in input.sections.items() if text.strip() and name in _EDITABLE_SECTIONS
        } or {name: text for name, text in input.sections.items() if text.strip()}
        section_scores: list[dict] = []
        for section_name, section_text in candidates.items():
            sec_vec = embedder.encode_single(section_text)
            section_scores.append({"section": section_name, "score": float(np.dot(sec_vec, jd_vec))})

        section_scores.sort(key=lambda x: x["score"])  # weakest first
        result = (overall_score, section_scores[:3], jd_vec)
        self._alignment_cache[key] = result
        return result

    @staticmethod
    def _drop_invented_title(tailored: str, source: str) -> str:
        """Models sometimes add a ``# Name`` title (and garble the name). Keep it only if it is verbatim in the source."""
        lines = tailored.splitlines()
        for i, line in enumerate(lines):
            if not line.strip():
                continue
            m = re.match(r"^#\s+(.+)$", line)
            if m and m.group(1).strip().strip("*").lower() not in source.lower():
                del lines[i]
                return "\n".join(lines).lstrip("\n")
            break
        return tailored

    @staticmethod
    def _coverage(text: str, jd: str) -> float:
        kws = extract_jd_keywords(jd, limit=25)
        if not kws:
            return 0.0
        have = terms_in(text)
        total = sum(k.score for k in kws) or 1.0
        return sum(k.score for k in kws if k.term in have) / total

    @staticmethod
    def _structure_preserved(original: str, tailored: str) -> tuple[bool, str]:
        """The rewrite must not silently drop most of the resume."""
        if len(tailored.strip()) < 0.6 * len(original.strip()):
            return False, "output is much shorter than the input (content dropped)"
        def bullets(t: str) -> list[str]:
            return [l for l in t.splitlines() if l.lstrip().startswith(("-", "*", "•"))]

        in_b, out_b = bullets(original), bullets(tailored)
        if len(in_b) >= 4 and len(out_b) < 0.75 * len(in_b):
            return False, f"bullets were merged or dropped ({len(in_b)} -> {len(out_b)})"
        longest_in = max((len(b.split()) for b in in_b), default=0)
        if out_b and max(len(b.split()) for b in out_b) > max(60, 2 * longest_in):
            return False, "a bullet is far longer than any original (entries were merged)"
        in_heads = [l for l in original.splitlines() if l.lstrip().startswith("#")]
        out_heads = [l for l in tailored.splitlines() if l.lstrip().startswith("#")]
        if in_heads and len(out_heads) < 0.6 * len(in_heads):
            return False, f"only {len(out_heads)} of {len(in_heads)} section headings kept"
        return True, ""

    def validate_input(self, input: AgentInput) -> None:
        if not input.content:
            raise ValueError("No resume content to tailor")
        if not input.job_description:
            raise ValueError("Job description required for tailoring")

    def validate_output(self, output: AgentOutput) -> None:
        if not output.metadata.get("grounded", True):
            g = output.metadata.get("grounding", {})
            raise QualityGateError(
                "Tailoring added claims absent from the resume "
                f"(numbers {g.get('novel_numbers', [])[:6]}, skills {g.get('injected_jd_terms', [])[:6]})"
            )
        if not output.metadata.get("structure_ok", True):
            raise QualityGateError(f"Tailoring dropped content: {output.metadata.get('structure_note')}")

    def _build_prompt(self, input: AgentInput, context: list, weaknesses: list[str]) -> str:
        context_text = "\n".join(f"- {seg.content} (score: {seg.score:.2f})" for seg in context)
        weakness_text = "\n".join(f"- {w}" for w in weaknesses) if weaknesses else "None detected"

        return f"""You are an expert resume tailoring specialist. Customize this resume for the job
description by reordering, emphasising and rewording — while staying strictly truthful.

TAILORING RULES — ALL MANDATORY:
1. REORDER: put the most JD-relevant experience, projects and skills first.
2. EMPHASISE: expand bullets that match JD requirements; condense unrelated ones. Never delete a section or a role, and never merge several bullets or roles into one — keep one output bullet per input bullet.
3. WORDING: where the resume ALREADY shows a skill the JD asks for, use the JD's exact term for it.
4. SKILLS SECTION: reorder to front-load skills the JD mentions. List only skills already in the resume.
5. SUMMARY/OBJECTIVE: if present, mirror the job title and the requirements the candidate genuinely meets.
6. ANTI-FABRICATION (non-negotiable): do NOT add any experience, skill, tool, number, metric or achievement that is
   not in the current resume. Do not add a skill because the JD asks for it. A gap stays a gap.
7. FORMAT: return the resume body in plain markdown — no code fences, no front matter, no name/title line. ## for sections, - for bullets.
{self._feedback}
NOTES FROM EARLIER ANALYSIS (gaps are for the candidate to consider — do NOT paper over them):
{weakness_text}

CURRENT RESUME:
{input.content}

TARGET JOB DESCRIPTION:
{input.job_description}

HIGH-RELEVANCE SEGMENTS (from RAG):
{context_text}

Return the COMPLETE tailored resume. Do not omit any section."""
