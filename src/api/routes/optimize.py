"""Optimization pipeline routes."""
from __future__ import annotations

import uuid

from fastapi import APIRouter

from src.api.schemas.resume import (
    AlignmentScoreRequest,
    AlignmentScoreResponse,
    OptimizeRequest,
    OptimizeResponse,
)

router = APIRouter()

# In-memory result store (no Redis/Celery needed for demo)
_results: dict[str, dict] = {}


@router.post("/optimize", response_model=OptimizeResponse)
async def optimize_resume(request: OptimizeRequest) -> OptimizeResponse:
    """Run the full optimization pipeline synchronously."""
    from src.llm.client import LLMClient
    from src.pipeline import Pipeline

    job_id = str(uuid.uuid4())

    llm = LLMClient()
    pipeline = Pipeline(llm_client=llm, user_id=job_id)
    results = await pipeline.run(
        request.resume_text,
        request.job_description,
        skip_interview=request.options.skip_interview_prep if request.options else False,
    )

    _results[job_id] = {
        "status": "completed",
        "results": {
            agent_name: {
                "content": output.content,
                "quality_score": output.quality_score,
                "suggestions": output.suggestions,
                "metadata": output.metadata,
            }
            for agent_name, output in results.items()
        },
    }

    return OptimizeResponse(
        status="ok",
        data={"job_id": job_id, "message": "Optimization pipeline completed"},
    )


@router.get("/optimize/{job_id}/status")
async def get_optimization_status(job_id: str) -> dict:
    """Check optimization job status."""
    job_status = "completed" if job_id in _results else "not_found"
    return {"status": "ok", "data": {"job_id": job_id, "job_status": job_status}}


@router.get("/optimize/{job_id}/result")
async def get_optimization_result(job_id: str) -> dict:
    """Get optimization results."""
    if job_id not in _results:
        return {
            "status": "error",
            "error": {"code": "NOT_READY", "message": "Job not found"},
        }
    return {"status": "ok", "data": _results[job_id]}


@router.post("/alignment/score", response_model=AlignmentScoreResponse)
async def score_alignment(request: AlignmentScoreRequest) -> AlignmentScoreResponse:
    """Score alignment between resume and job description."""
    from src.rag.embedder import Embedder
    from src.scoring.alignment import AlignmentScorer

    embedder = Embedder()
    scorer = AlignmentScorer(embedder)
    sections = {"content": request.resume_text}
    jd_lines = [l.strip() for l in request.job_description.split("\n") if l.strip()]
    result = scorer.score(sections, jd_lines)

    return AlignmentScoreResponse(
        status="ok",
        data={
            "overall_score": round(result.overall_score, 3),
            "gaps": result.gaps[:5],
            "section_scores": {k: round(v, 3) for k, v in result.section_scores.items()},
        },
    )
