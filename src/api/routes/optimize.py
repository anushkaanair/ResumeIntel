"""Optimization pipeline routes — Redis-backed results + real-time pub/sub events."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import structlog
from fastapi import APIRouter

from src.api.schemas.resume import (
    AlignmentScoreRequest,
    AlignmentScoreResponse,
    OptimizeRequest,
    OptimizeResponse,
)
from src.db.redis_store import rget, rpublish, rset

logger = structlog.get_logger()
router = APIRouter()

JOB_KEY = "job:{job_id}"
WS_CHANNEL = "pipeline:{job_id}"


async def broadcast(job_id: str, event: dict[str, Any]) -> None:
    """Publish pipeline event to Redis channel for WebSocket consumers."""
    await rpublish(WS_CHANNEL.format(job_id=job_id), event)


# Strong references so background pipeline tasks are not garbage-collected mid-run.
_running: set[asyncio.Task] = set()
# Each pipeline makes dozens of LLM calls and holds model state; run at most two at once.
_slots = asyncio.Semaphore(2)


async def _run_job(job_id: str, request: OptimizeRequest) -> None:
    from src.llm.client import LLMClient
    from src.pipeline import Pipeline

    async def emit(event: dict[str, Any]) -> None:
        await broadcast(job_id, event)

    try:
        async with _slots:
            pipeline = Pipeline(llm_client=LLMClient(), user_id=job_id)
            result = await pipeline.run(
                request.resume_text,
                request.job_description,
                skip_interview=request.options.skip_interview_prep if request.options else False,
                emit=emit,
            )
        await rset(JOB_KEY.format(job_id=job_id), {"status": "completed", **result})
    except Exception as e:  # noqa: BLE001
        cause = (getattr(e, "context", None) or {}).get("last_error") or str(e)
        logger.error("optimize.job_failed", job_id=job_id, error=str(cause)[:500])
        await rset(JOB_KEY.format(job_id=job_id), {"status": "error", "error": str(cause)[:500]})
        await broadcast(job_id, {
            "event_type": "PIPELINE_ERROR",
            "agent_id": None,
            "data": {"message": str(cause)[:500]},
            "message": f"Pipeline error: {cause}"[:600],
        })


@router.post("/optimize", response_model=OptimizeResponse)
async def optimize_resume(request: OptimizeRequest) -> OptimizeResponse:
    """Start the optimization pipeline in the background and return its job id.

    Progress streams over ``/ws/optimize/{job_id}``; the finished result is read
    from ``/optimize/{job_id}/result``.
    """
    job_id = str(uuid.uuid4())
    await rset(JOB_KEY.format(job_id=job_id), {"status": "running"})
    task = asyncio.create_task(_run_job(job_id, request))
    _running.add(task)
    task.add_done_callback(_running.discard)
    return OptimizeResponse(status="ok", data={"job_id": job_id, "message": "Optimization started"})


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
    if data.get("status") == "error":
        return {"status": "error", "error": {"code": "PIPELINE_FAILED", "message": data.get("error", "Pipeline failed")}}
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
