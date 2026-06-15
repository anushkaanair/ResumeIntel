"""Interview API routes — real agent integration + adaptive difficulty (patent claim 9)."""

from __future__ import annotations

import json
import re
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.db.redis_store import rget, rset

router = APIRouter()

_INTERVIEW_KEY = "interview:{job_id}"
_PERF_KEY = "interview_perf:{job_id}"


class GenerateInterviewRequest(BaseModel):
    resume_text: str
    job_description: str
    resume_id: str = ""


class PracticeAnswerRequest(BaseModel):
    user_answer: str = Field(..., min_length=10)
    question_text: str = ""
    question_category: str = "behavioral"
    job_description: str = ""
    resume_text: str = ""


# ─── 4-dimensional performance vector ────────────────────────────────────────

READINESS_TIERS = {
    "Beginner":     (0.0, 0.4),
    "Intermediate": (0.4, 0.65),
    "Advanced":     (0.65, 0.82),
    "Expert":       (0.82, 1.0),
}

DIMENSION_KEYS = [
    "technical_depth_score",
    "behavioral_clarity_score",
    "communication_structure_score",
    "domain_knowledge_score",
]


def _default_vector() -> dict[str, float]:
    return {k: 0.5 for k in DIMENSION_KEYS}


def _compute_tier(vector: dict[str, float]) -> str:
    avg = sum(vector.values()) / len(vector)
    for tier, (lo, hi) in READINESS_TIERS.items():
        if lo <= avg < hi:
            return tier
    return "Expert"


def _update_vector(
    vector: dict[str, float],
    category: str,
    scores: dict[str, float],
) -> dict[str, float]:
    """Recalculate rolling performance vector after an answered question."""
    new = dict(vector)
    if category in ("technical", "role_specific"):
        new["technical_depth_score"] = _rolling(new["technical_depth_score"], scores.get("technical_depth", 0.5))
        new["domain_knowledge_score"] = _rolling(new["domain_knowledge_score"], scores.get("domain_knowledge", 0.5))
    elif category in ("behavioral", "company_specific"):
        new["behavioral_clarity_score"] = _rolling(new["behavioral_clarity_score"], scores.get("behavioral_clarity", 0.5))
        new["communication_structure_score"] = _rolling(new["communication_structure_score"], scores.get("communication_structure", 0.5))
    return new


def _rolling(prev: float, new: float, weight: float = 0.35) -> float:
    """Exponential rolling average."""
    return round(prev * (1 - weight) + new * weight, 3)


# ─── Routes ──────────────────────────────────────────────────────────────────


@router.post("/interview/{job_id}/generate")
async def generate_interview(job_id: str, request: GenerateInterviewRequest) -> dict:
    """Run InterviewAgent and store structured prep material."""
    from src.agents.base_agent import AgentInput
    from src.agents.interview_agent import InterviewAgent
    from src.llm.client import LLMClient
    from src.rag.embedder import Embedder
    from src.rag.retriever import Retriever
    from src.rag.vector_store import VectorStore

    llm = LLMClient()
    embedder = Embedder()
    vs = VectorStore()
    retriever = Retriever(embedder, vs, user_id=f"interview_{job_id}")

    # Index resume segments
    segments = [
        {"content": s.strip(), "segment_id": f"s{i}", "section": "resume"}
        for i, s in enumerate(request.resume_text.split("\n"))
        if s.strip() and len(s.strip()) > 20
    ]
    if segments:
        await retriever.index_segments(segments)

    agent = InterviewAgent(retriever, llm)
    agent_input = AgentInput(
        content=request.resume_text,
        job_description=request.job_description,
    )
    output = await agent.run(agent_input)

    # Parse LLM output into structured format
    questions = _parse_questions(output.content)
    await rset(_INTERVIEW_KEY.format(job_id=job_id), {
        "job_id": job_id,
        "resume_id": request.resume_id,
        "raw_content": output.content,
        "questions": questions,
        "quality_score": output.quality_score,
        "provenance": {
            "agent_name": "InterviewAgent",
            "confidence": output.quality_score,
        } if output.provenance else None,
    })

    await rset(_PERF_KEY.format(job_id=job_id), {
        "vector": _default_vector(),
        "questions_answered": 0,
        "tier": "Intermediate",
    })

    return {
        "status": "ok",
        "data": {
            "job_id": job_id,
            "questions": questions,
            "tier": "Intermediate",
            "performance_vector": _default_vector(),
        },
    }


@router.get("/interview/{job_id}")
async def get_interview_data(job_id: str) -> dict:
    """Fetch stored interview prep data or return placeholder."""
    stored = await rget(_INTERVIEW_KEY.format(job_id=job_id))
    if stored:
        perf = await rget(_PERF_KEY.format(job_id=job_id)) or {}
        return {
            "status": "ok",
            "data": {
                **stored,
                "tier": perf.get("tier", "Intermediate"),
                "performance_vector": perf.get("vector", _default_vector()),
                "questions_answered": perf.get("questions_answered", 0),
            },
        }
    return {
        "status": "ok",
        "data": {
            "job_id": job_id,
            "message": "Interview prep not yet generated. POST /interview/{job_id}/generate first.",
            "questions": [],
            "tier": "Intermediate",
            "performance_vector": _default_vector(),
        },
    }


@router.post("/interview/question/{question_id}/answer")
async def practice_answer(question_id: str, request: PracticeAnswerRequest) -> dict:
    """Score a practice answer and update the 4-dim performance vector."""
    from src.llm.client import LLMClient

    llm = LLMClient()

    # Score with LLM on 4 dimensions
    prompt = f"""You are an expert interview coach. Score this practice answer on 4 dimensions (0.0-1.0 each).

QUESTION: {request.question_text or 'General interview question'}
CATEGORY: {request.question_category}
ANSWER: {request.user_answer}

JOB DESCRIPTION CONTEXT: {request.job_description[:300] if request.job_description else 'Not provided'}

Score each dimension:
1. technical_depth: depth and accuracy of technical content
2. behavioral_clarity: STAR structure and story clarity
3. communication_structure: organization, flow, conciseness
4. domain_knowledge: domain-specific accuracy and insight

Also provide:
- strengths: 2-3 specific strengths
- improvements: 2-3 specific improvement suggestions
- improved_answer: a brief model answer example (2-3 sentences)

Format response as JSON:
{{
  "technical_depth": 0.0-1.0,
  "behavioral_clarity": 0.0-1.0,
  "communication_structure": 0.0-1.0,
  "domain_knowledge": 0.0-1.0,
  "strengths": ["...", "..."],
  "improvements": ["...", "..."],
  "improved_answer": "..."
}}"""

    raw = await llm.generate(prompt)

    # Parse JSON response
    scores: dict[str, Any] = {}
    try:
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            scores = json.loads(json_match.group())
    except Exception:
        pass

    dim_scores = {
        "technical_depth": float(scores.get("technical_depth", 0.6)),
        "behavioral_clarity": float(scores.get("behavioral_clarity", 0.6)),
        "communication_structure": float(scores.get("communication_structure", 0.6)),
        "domain_knowledge": float(scores.get("domain_knowledge", 0.6)),
    }

    # Find the job_id by searching performance store (question_id prefix)
    # Simple approach: use question_id to find associated job
    job_id = question_id.split("_")[0] if "_" in question_id else question_id
    perf = await rget(_PERF_KEY.format(job_id=job_id)) or {
        "vector": _default_vector(), "questions_answered": 0, "tier": "Intermediate"
    }

    new_vector = _update_vector(perf["vector"], request.question_category, dim_scores)
    questions_answered = perf["questions_answered"] + 1

    # Recalculate tier every 3 questions per patent claim 9
    new_tier = perf["tier"]
    if questions_answered % 3 == 0:
        new_tier = _compute_tier(new_vector)

    await rset(_PERF_KEY.format(job_id=job_id), {
        "vector": new_vector,
        "questions_answered": questions_answered,
        "tier": new_tier,
    })

    overall_score = int(sum(dim_scores.values()) / len(dim_scores) * 100)

    return {
        "status": "ok",
        "data": {
            "score": overall_score,
            "dimension_scores": dim_scores,
            "performance_vector": new_vector,
            "tier": new_tier,
            "tier_changed": new_tier != perf["tier"],
            "questions_answered": questions_answered,
            "strengths": scores.get("strengths", ["Good structure", "Clear delivery"]),
            "improvements": scores.get("improvements", ["Add more specifics", "Include metrics"]),
            "improved_answer": scores.get("improved_answer", ""),
        },
    }


def _parse_questions(content: str) -> list[dict[str, Any]]:
    """Parse InterviewAgent output into structured question list."""
    questions: list[dict[str, Any]] = []
    lines = content.split("\n")
    q_idx = 0
    current_category = "behavioral"

    for line in lines:
        lower = line.lower()
        if "behavioral" in lower and line.startswith("##"):
            current_category = "behavioral"
        elif "technical" in lower and line.startswith("##"):
            current_category = "technical"
        elif "talking point" in lower and line.startswith("##"):
            current_category = "talking_point"
        elif line.strip().startswith("**Q") and ":" in line:
            q_text = re.sub(r"\*\*Q\d+:\s*", "", line).replace("**", "").strip()
            if q_text:
                q_idx += 1
                questions.append({
                    "id": f"q{q_idx}",
                    "text": q_text,
                    "category": current_category,
                    "difficulty": "medium",
                    "source": "interview_agent",
                    "talkingPoints": [],
                })
        elif questions and line.strip().startswith("-"):
            questions[-1]["talkingPoints"].append(line.strip().lstrip("- "))

    return questions
