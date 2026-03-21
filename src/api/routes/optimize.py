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

# In-memory job store (replace with Redis/DB in production)
_jobs: dict[str, dict] = {}


@router.post("/optimize", response_model=OptimizeResponse)
async def optimize_resume(request: OptimizeRequest) -> OptimizeResponse:
    """Start the full optimization pipeline on a resume."""
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "queued", "result": None}

    # TODO: dispatch to Celery worker for async processing
    # For now, return job_id for polling
    return OptimizeResponse(
        status="ok",
        data={"job_id": job_id, "message": "Optimization pipeline started"},
    )


@router.get("/optimize/{job_id}/status")
async def get_optimization_status(job_id: str) -> dict:
    """Check optimization job status."""
    job = _jobs.get(job_id)
    if not job:
        return {"status": "error", "error": {"code": "NOT_FOUND", "message": "Job not found"}}
    return {"status": "ok", "data": {"job_id": job_id, "job_status": job["status"]}}


@router.get("/optimize/{job_id}/result")
async def get_optimization_result(job_id: str) -> dict:
    """Get optimization results."""
    job = _jobs.get(job_id)
    if not job:
        return {"status": "error", "error": {"code": "NOT_FOUND", "message": "Job not found"}}
    if job["status"] != "completed":
        return {"status": "error", "error": {"code": "NOT_READY", "message": "Job not completed"}}
    return {"status": "ok", "data": job["result"]}


@router.post("/alignment/score", response_model=AlignmentScoreResponse)
async def score_alignment(request: AlignmentScoreRequest) -> AlignmentScoreResponse:
    """Score alignment between resume and job description."""
    from src.rag.embedder import Embedder
    from src.scoring.alignment import AlignmentScorer

    embedder = Embedder()
    scorer = AlignmentScorer(embedder)

    # Simple section split for scoring
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
