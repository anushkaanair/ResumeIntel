"""WebSocket endpoint — real pipeline events via Redis pub/sub (patent claim 12)."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/ws/optimize/{job_id}")
async def websocket_optimize(websocket: WebSocket, job_id: str):
    """Stream real agent pipeline events from Redis pub/sub to the frontend.

    The optimize route publishes AgentEvent dicts to channel pipeline:{job_id}.
    This endpoint subscribes and forwards them to the connected browser.
    Terminates on PIPELINE_COMPLETE, PIPELINE_ERROR, or client disconnect.
    """
    await websocket.accept()

    from src.db.redis_store import rsubscribe

    pubsub, redis_conn = await rsubscribe(f"pipeline:{job_id}")

    async def _listen():
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            event = json.loads(message["data"])
            try:
                await websocket.send_json(event)
            except Exception:
                return
            if event.get("event_type") in ("PIPELINE_COMPLETE", "PIPELINE_ERROR", "ALIGNMENT_GATE_ABORT"):
                return

    try:
        # Run listener with a timeout — auto-close if pipeline takes > 10 min
        await asyncio.wait_for(_listen(), timeout=600)
    except asyncio.TimeoutError:
        try:
            await websocket.send_json({
                "event_type": "PIPELINE_ERROR",
                "agent_id": None,
                "data": {"message": "Pipeline timed out after 10 minutes"},
                "message": "Timeout",
            })
        except Exception:
            pass
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({
                "event_type": "PIPELINE_ERROR",
                "agent_id": None,
                "data": {"message": str(e)},
                "message": f"WebSocket error: {e}",
            })
        except Exception:
            pass
    finally:
        await pubsub.unsubscribe(f"pipeline:{job_id}")
        await redis_conn.aclose()
