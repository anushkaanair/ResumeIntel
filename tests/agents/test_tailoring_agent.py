"""Tests for TailoringAgent."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from src.agents.base_agent import AgentInput
from src.agents.tailoring_agent import AlignmentGateError, TailoringAgent
from src.exceptions import AgentError, NonRetryableError

HONEST_TAILORED = (
    "## Summary\nExperienced software engineer with 5 years of Python development.\n\n"
    "## Experience\n"
    "- Built REST API serving 10K requests/day with 99.9% uptime\n"
    "- Led migration of monolithic app to microservices architecture\n"
    "- Implemented CI/CD pipeline reducing deployment time by 60%\n"
    "- Worked on database optimization improving query performance\n\n"
    "## Education\nB.S. Computer Science, MIT, 2018\n\n"
    "## Skills\nPython, FastAPI, PostgreSQL, Docker, AWS, JavaScript, React, Git"
)


def _agent(retriever, llm, embedder) -> TailoringAgent:
    retriever.embedder = embedder
    return TailoringAgent(retriever=retriever, llm_client=llm)


def _input(resume: str, jd: str) -> AgentInput:
    return AgentInput(
        content=resume, job_description=jd,
        sections={"experience": "Built REST API", "skills": "Python"},
        metadata={"source_text": resume},
    )


def _llm(text: str) -> AsyncMock:
    llm = AsyncMock()
    llm.generate.return_value = text
    return llm


@pytest.mark.asyncio
async def test_tailoring_returns_grounded_content(mock_retriever, mock_embedder, sample_resume, sample_jd) -> None:
    result = await _agent(mock_retriever, _llm(HONEST_TAILORED), mock_embedder).run(_input(sample_resume, sample_jd))
    assert result.content.strip()
    assert result.metadata["grounded"] is True
    assert result.quality_score >= 0.7
    assert "pre_tailoring_alignment" in result.metadata


@pytest.mark.asyncio
async def test_tailoring_requires_job_description(mock_retriever, mock_llm, sample_resume) -> None:
    with pytest.raises(Exception):
        await TailoringAgent(mock_retriever, mock_llm).run(AgentInput(content=sample_resume, job_description=""))


@pytest.mark.asyncio
async def test_keyword_salad_that_adds_skills_is_rejected(mock_retriever, mock_embedder, sample_resume, sample_jd) -> None:
    """Stuffing the JD's keywords into the resume used to pass the gate. It must not."""
    resume = sample_resume.replace("Docker, AWS, ", "")  # resume genuinely lacks Docker and AWS
    salad = HONEST_TAILORED.replace("Docker, AWS, ", "") + "\n- Deployed Docker containers on AWS with Django"
    with pytest.raises(AgentError) as exc:
        await _agent(mock_retriever, _llm(salad), mock_embedder).run(_input(resume, sample_jd))
    assert "absent from the resume" in exc.value.context["last_error"]


@pytest.mark.asyncio
async def test_rewrite_that_drops_content_is_rejected(mock_retriever, mock_embedder, sample_resume, sample_jd) -> None:
    with pytest.raises(AgentError):
        await _agent(mock_retriever, _llm("## Skills\nPython"), mock_embedder).run(_input(sample_resume, sample_jd))


@pytest.mark.asyncio
async def test_alignment_gate_is_not_retried(mock_retriever, sample_resume, sample_jd) -> None:
    emb = MagicMock()
    vecs = iter([np.array([1, 0, 0, 0], dtype="float32"), np.array([0, 1, 0, 0], dtype="float32")] * 5)
    emb.encode_single.side_effect = lambda _t: next(vecs)
    llm = _llm(HONEST_TAILORED)
    with pytest.raises(AlignmentGateError) as exc:
        await _agent(mock_retriever, llm, emb).run(_input(sample_resume, sample_jd))
    assert isinstance(exc.value, NonRetryableError)
    assert exc.value.alignment_score == pytest.approx(0.0)
    llm.generate.assert_not_awaited()
    assert emb.encode_single.call_count <= 6  # one attempt: resume, JD, up to 2 sections-ish; not 3x


def test_invented_title_is_dropped_but_a_real_one_is_kept() -> None:
    src = "Anushka Nair\n## Experience\n- Built things"
    bad = "# Anushka Anair\n\n## Experience\n- Built things"
    good = "# Anushka Nair\n\n## Experience\n- Built things"
    assert not TailoringAgent._drop_invented_title(bad, src).startswith("#  ")
    assert TailoringAgent._drop_invented_title(bad, src).startswith("## Experience")
    assert TailoringAgent._drop_invented_title(good, src) == good


def test_clean_markdown_strips_fence_and_front_matter() -> None:
    from src.llm.client import clean_markdown

    raw = "```markdown\n---\nlayout: resume\n---\n\n## Experience\n- x\n```"
    assert clean_markdown(raw) == "## Experience\n- x"
    assert clean_markdown("## A\n- b") == "## A\n- b"


def test_merged_bullets_fail_the_structure_check() -> None:
    original = "## Experience\n" + "\n".join(f"- Built service number {i} with Python and tests" for i in range(6))
    merged = "## Experience\n- " + " ".join(f"Built service number {i} with Python and tests" for i in range(6))
    ok, note = TailoringAgent._structure_preserved(original, merged)
    assert not ok and "merged" in note
    assert TailoringAgent._structure_preserved(original, original)[0]


@pytest.mark.asyncio
async def test_gate_scores_the_original_resume_not_the_trimmed_rewrite(mock_retriever, sample_resume, sample_jd) -> None:
    """The threshold was calibrated on full resumes; the trimmed Quality output must not be what is gated."""
    seen: list[str] = []
    emb = MagicMock()
    emb.encode_single.side_effect = lambda t: (seen.append(t), np.ones(4, dtype="float32") / 2)[1]
    agent = _agent(mock_retriever, _llm(HONEST_TAILORED), emb)
    inp = _input("- trimmed bullet only", sample_jd)
    inp.metadata["source_text"] = sample_resume
    await agent.run(inp)
    assert seen[0] == sample_resume
