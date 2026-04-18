"""Optimization pipeline routes."""
from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, BackgroundTasks

from src.api.routes.ws import get_or_create_job_queue, publish_event
from src.api.schemas.resume import (
    AlignmentScoreRequest,
    AlignmentScoreResponse,
    OptimizeRequest,
    OptimizeResponse,
)

router = APIRouter()

# In-memory result store (replace with PostgreSQL when DB integration is wired)
_results: dict[str, dict] = {}


@router.post("/optimize", response_model=OptimizeResponse)
async def optimize_resume(
    request: OptimizeRequest,
    background_tasks: BackgroundTasks,
) -> OptimizeResponse:
    """Start the optimization pipeline and return a job_id immediately.

    Pipeline runs in a FastAPI BackgroundTask. Per-agent events are pushed to
    the job's asyncio.Queue so the WebSocket handler can forward them live.
    """
    job_id = str(uuid.uuid4())

    # Register the queue before launching so the WS client can connect immediately
    queue = get_or_create_job_queue(job_id)

    background_tasks.add_task(
        _run_pipeline_task,
        job_id=job_id,
        resume_text=request.resume_text,
        job_description=request.job_description,
        skip_interview=(
            request.options.skip_interview_prep if request.options else False
        ),
        queue=queue,
    )

    return OptimizeResponse(
        status="ok",
        data={"job_id": job_id, "message": "Optimization pipeline started"},
    )


async def _run_pipeline_task(
    job_id: str,
    resume_text: str,
    job_description: str,
    skip_interview: bool,
    queue: asyncio.Queue,
) -> None:
    """Background task: runs pipeline and pushes AgentEvents into the job queue."""
    from src.llm.client import LLMClient
    from src.pipeline import Pipeline

    async def _callback(event: dict) -> None:
        await publish_event(job_id, event)

    try:
        llm = LLMClient()
        pipeline = Pipeline(llm_client=llm, user_id=job_id)
        results = await pipeline.run(
            resume_text,
            job_description,
            skip_interview=skip_interview,
            event_callback=_callback,
        )

        _results[job_id] = {
            "status": "completed",
            "results": {
                agent_name: {
                    "content": output.content,
                    "quality_score": output.quality_score,
                    "status": output.status,
                    "suggestions": output.suggestions,
                    "metadata": output.metadata,
                }
                for agent_name, output in results.items()
            },
        }

    except Exception as exc:
        _results[job_id] = {"status": "error", "error": str(exc)}
        # Push error event so WS client knows the pipeline failed
        await publish_event(job_id, {
            "event_type": "error",
            "agent_name": "",
            "timestamp": "",
            "quality_gate_passed": False,
            "quality_score": None,
            "partial_result": {},
            "message": str(exc),
        })


@router.get("/optimize/{job_id}/status")
async def get_optimization_status(job_id: str) -> dict:
    """Check optimization job status."""
    if job_id not in _results:
        return {"status": "ok", "data": {"job_id": job_id, "job_status": "running"}}
    return {
        "status": "ok",
        "data": {"job_id": job_id, "job_status": _results[job_id]["status"]},
    }


@router.get("/optimize/{job_id}/result")
async def get_optimization_result(job_id: str) -> dict:
    """Get optimization results once the pipeline has completed."""
    if job_id not in _results:
        return {
            "status": "error",
            "error": {"code": "NOT_READY", "message": "Job not found or still running"},
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
