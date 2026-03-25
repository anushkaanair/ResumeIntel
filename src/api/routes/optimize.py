"""Optimization pipeline routes — Redis-backed results + real-time pub/sub events."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter

from src.api.schemas.resume import (
    AlignmentScoreRequest,
    AlignmentScoreResponse,
    OptimizeRequest,
    OptimizeResponse,
)
from src.db.redis_store import rget, rpublish, rset

router = APIRouter()

JOB_KEY = "job:{job_id}"
WS_CHANNEL = "pipeline:{job_id}"


async def broadcast(job_id: str, event: dict[str, Any]) -> None:
    """Publish pipeline event to Redis channel for WebSocket consumers."""
    await rpublish(WS_CHANNEL.format(job_id=job_id), event)


@router.post("/optimize", response_model=OptimizeResponse)
async def optimize_resume(request: OptimizeRequest) -> OptimizeResponse:
    """Run the full optimization pipeline, streaming events via Redis pub/sub."""
    from src.llm.client import LLMClient
    from src.pipeline import Pipeline

    job_id = str(uuid.uuid4())
    await rset(JOB_KEY.format(job_id=job_id), {"status": "running"})

    llm = LLMClient()
    pipeline = Pipeline(llm_client=llm, user_id=job_id)

    async def emit(event: dict[str, Any]) -> None:
        await broadcast(job_id, event)

    try:
        result = await pipeline.run(
            request.resume_text,
            request.job_description,
            skip_interview=request.options.skip_interview_prep if request.options else False,
            emit=emit,
        )
        await rset(JOB_KEY.format(job_id=job_id), {"status": "completed", **result})
    except Exception as e:
        await rset(JOB_KEY.format(job_id=job_id), {"status": "error", "error": str(e)})
        await broadcast(job_id, {
            "event_type": "PIPELINE_ERROR",
            "agent_id": None,
            "data": {"message": str(e)},
            "message": f"Pipeline error: {e}",
        })
        raise

    return OptimizeResponse(
        status="ok",
        data={"job_id": job_id, "message": "Optimization pipeline completed"},
    )


@router.get("/optimize/{job_id}/status")
async def get_optimization_status(job_id: str) -> dict:
    data = await rget(JOB_KEY.format(job_id=job_id))
    if not data:
        return {"status": "ok", "data": {"job_id": job_id, "job_status": "not_found"}}
    return {"status": "ok", "data": {"job_id": job_id, "job_status": data.get("status", "unknown")}}


@router.get("/optimize/{job_id}/result")
async def get_optimization_result(job_id: str) -> dict:
    data = await rget(JOB_KEY.format(job_id=job_id))
    if not data:
        return {"status": "error", "error": {"code": "NOT_READY", "message": "Job not found"}}
    return {"status": "ok", "data": data}


@router.post("/alignment/score", response_model=AlignmentScoreResponse)
async def score_alignment(request: AlignmentScoreRequest) -> AlignmentScoreResponse:
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
