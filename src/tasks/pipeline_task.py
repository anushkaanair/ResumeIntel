"""Celery task — runs the full multi-agent optimization pipeline."""
from __future__ import annotations

import asyncio

import structlog

from src.llm.client import LLMClient
from src.pipeline import Pipeline
from src.tasks.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(bind=True, name="tasks.run_pipeline")
def run_pipeline_task(
    self,
    job_id: str,
    resume_text: str,
    job_description: str,
    skip_interview: bool = False,
) -> dict:
    """Run the full optimization pipeline as a Celery task.

    Args:
        job_id: Unique identifier for this optimization run (used as user_id).
        resume_text: Plain-text resume content.
        job_description: Plain-text job description.
        skip_interview: When True, the interview-prep agent is skipped.

    Returns:
        Serialized pipeline results keyed by agent name.
    """
    logger.info("task.start", job_id=job_id)

    try:
        self.update_state(state="STARTED", meta={"job_id": job_id, "status": "running"})

        llm = LLMClient()
        pipeline = Pipeline(llm_client=llm, user_id=job_id)

        # Run the async pipeline in this sync Celery worker context.
        # asyncio.run() creates a fresh event loop — safe in Celery worker threads (Python 3.10+).
        results = asyncio.run(
            pipeline.run(resume_text, job_description, skip_interview=skip_interview)
        )

        # Serialize AgentOutput objects to plain dicts for JSON storage.
        serialized = {
            agent_name: {
                "content": output.content,
                "quality_score": output.quality_score,
                "suggestions": output.suggestions,
                "metadata": output.metadata,
            }
            for agent_name, output in results.items()
        }

        logger.info("task.complete", job_id=job_id)
        return {"status": "completed", "results": serialized}

    except Exception as e:
        logger.error("task.failed", job_id=job_id, error=str(e))
        raise
