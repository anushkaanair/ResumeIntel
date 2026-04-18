"""WebSocket endpoint for real-time pipeline events.

Architecture:
  - optimize.py creates an asyncio.Queue per job_id via get_or_create_job_queue()
  - pipeline.py calls publish_event(job_id, event) after each agent completes
  - This WS handler reads from that queue and forwards events to the client
  - Falls back to mock stream if no queue exists (e.g. direct WS connection before job starts)
"""
from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

logger = structlog.get_logger()
router = APIRouter()

# ---------------------------------------------------------------------------
# Per-job event queues — keyed by job_id
# ---------------------------------------------------------------------------

_job_queues: dict[str, asyncio.Queue] = {}
_QUEUE_TTL_SECONDS = 600  # queues cleaned up after 10 min of inactivity


def get_or_create_job_queue(job_id: str) -> asyncio.Queue:
    """Return (creating if necessary) the event queue for a pipeline job."""
    if job_id not in _job_queues:
        _job_queues[job_id] = asyncio.Queue()
    return _job_queues[job_id]


def remove_job_queue(job_id: str) -> None:
    _job_queues.pop(job_id, None)


# ---------------------------------------------------------------------------
# Typed event schema
# ---------------------------------------------------------------------------

class AgentEvent(BaseModel):
    event_type: str          # "agent_start" | "agent_complete" | "gate_failed" | "pipeline_complete" | "error"
    agent_name: str          # "ingestion" | "generation" | "quality" | "weak_detection" | "tailoring" | "interview"
    timestamp: str           # ISO 8601
    quality_gate_passed: bool | None = None
    quality_score: float | None = None
    partial_result: dict[str, Any] = {}
    message: str = ""


def make_event(
    event_type: str,
    agent_name: str,
    *,
    gate_passed: bool | None = None,
    quality_score: float | None = None,
    partial_result: dict | None = None,
    message: str = "",
) -> dict:
    return AgentEvent(
        event_type=event_type,
        agent_name=agent_name,
        timestamp=datetime.now(timezone.utc).isoformat(),
        quality_gate_passed=gate_passed,
        quality_score=quality_score,
        partial_result=partial_result or {},
        message=message,
    ).model_dump()


async def publish_event(job_id: str, event: dict) -> None:
    """Called by pipeline.py to push an agent event to the client queue."""
    queue = _job_queues.get(job_id)
    if queue is not None:
        await queue.put(event)


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------

POLL_INTERVAL = 0.1   # seconds between queue checks
CLIENT_TIMEOUT = 300  # seconds before we close a stale connection


@router.websocket("/ws/optimize/{job_id}")
async def websocket_optimize(websocket: WebSocket, job_id: str):
    """Stream real pipeline events to the frontend.

    Reads from the per-job asyncio.Queue populated by pipeline.py.
    Sends a 'pipeline_complete' sentinel (or 'error') then closes.
    """
    await websocket.accept()
    logger.info("ws.client_connected", job_id=job_id)

    queue = _job_queues.get(job_id)

    try:
        if queue is not None:
            await _stream_real_events(websocket, job_id, queue)
        else:
            # Queue not yet created — wait briefly for pipeline to start
            await _wait_for_queue_then_stream(websocket, job_id)
    except WebSocketDisconnect:
        logger.info("ws.client_disconnected", job_id=job_id)
    except Exception as exc:
        logger.error("ws.error", job_id=job_id, error=str(exc))
        try:
            await websocket.send_json({
                "event_type": "error",
                "agent_name": "",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": str(exc),
            })
        except Exception:
            pass
    finally:
        remove_job_queue(job_id)


async def _wait_for_queue_then_stream(websocket: WebSocket, job_id: str) -> None:
    """Poll briefly for the queue to appear (pipeline may start after WS connects)."""
    deadline = time.monotonic() + 10  # wait up to 10s for pipeline to register
    while time.monotonic() < deadline:
        queue = _job_queues.get(job_id)
        if queue is not None:
            await _stream_real_events(websocket, job_id, queue)
            return
        await asyncio.sleep(0.2)

    # Pipeline never started — nothing to stream
    await websocket.send_json(make_event(
        "error", "",
        message=f"No pipeline found for job {job_id}. Start optimization first.",
    ))


async def _stream_real_events(
    websocket: WebSocket, job_id: str, queue: asyncio.Queue
) -> None:
    """Drain the queue and forward each event to the client."""
    deadline = time.monotonic() + CLIENT_TIMEOUT

    while time.monotonic() < deadline:
        try:
            event = queue.get_nowait()
        except asyncio.QueueEmpty:
            await asyncio.sleep(POLL_INTERVAL)
            continue

        await websocket.send_json(event)

        # Stop streaming once the terminal event arrives
        if event.get("event_type") in ("pipeline_complete", "error"):
            break
