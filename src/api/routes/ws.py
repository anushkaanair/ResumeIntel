"""WebSocket endpoint for real-time pipeline events.

Simulates the agent pipeline event stream for frontend development.
"""
from __future__ import annotations

import asyncio
import json
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

AGENTS = [
    ("A_ing", "Ingestion", 1.5),
    ("A_gen", "Generation", 2.0),
    ("A_qual", "Quality", 2.5),
    ("A_weak", "Weak Detection", 1.5),
    ("A_tail", "Tailoring", 2.5),
    ("A_int", "Interview", 3.0),
]

MOCK_METRICS_PER_AGENT = {
    "A_ing": {"alignment": 0.45, "keywordCoverage": 35, "impactScore": 0.38, "atsPassRate": 32},
    "A_gen": {"alignment": 0.52, "keywordCoverage": 42, "impactScore": 0.45, "atsPassRate": 40},
    "A_qual": {"alignment": 0.62, "keywordCoverage": 55, "impactScore": 0.72, "atsPassRate": 58},
    "A_weak": {"alignment": 0.65, "keywordCoverage": 60, "impactScore": 0.78, "atsPassRate": 63},
    "A_tail": {"alignment": 0.82, "keywordCoverage": 85, "impactScore": 0.81, "atsPassRate": 82},
    "A_int": {"alignment": 0.82, "keywordCoverage": 85, "impactScore": 0.81, "atsPassRate": 82},
}


@router.websocket("/ws/optimize/{job_id}")
async def websocket_optimize(websocket: WebSocket, job_id: str):
    """Simulates the pipeline WebSocket event stream.

    Emits AGENT_START → AGENT_GATE_PASS → AGENT_COMPLETE for each agent.
    Finishes with PIPELINE_COMPLETE.
    """
    await websocket.accept()

    try:
        for agent_id, agent_name, delay in AGENTS:
            # AGENT_START
            await websocket.send_json(
                {
                    "event_type": "AGENT_START",
                    "agent_id": agent_id,
                    "timestamp": time.time(),
                    "data": {},
                    "message": f"{agent_name} agent started",
                }
            )

            # Simulate processing
            await asyncio.sleep(delay)

            # AGENT_GATE_PASS
            metrics = MOCK_METRICS_PER_AGENT.get(agent_id, {})
            bullet_updates = []
            keyword_updates = []

            if agent_id == "A_qual":
                bullet_updates = [
                    {
                        "bulletId": "b4",
                        "optimizedText": "Developed gradient-boosted ML recommendation engine achieving 94% accuracy (+18% over baseline), driving $2.1M incremental revenue",
                        "impactScore": 0.89,
                    },
                    {
                        "bulletId": "b5",
                        "optimizedText": "Optimized PostgreSQL query performance by 340% through index restructuring, supporting 2M+ daily transactions",
                        "impactScore": 0.85,
                    },
                ]
            elif agent_id == "A_tail":
                keyword_updates = [
                    {"keyword": "Kubernetes", "matched": False},
                    {"keyword": "GraphQL", "matched": False},
                    {"keyword": "PostgreSQL", "matched": True},
                ]

            await websocket.send_json(
                {
                    "event_type": "AGENT_GATE_PASS",
                    "agent_id": agent_id,
                    "timestamp": time.time(),
                    "data": {
                        "metrics": metrics,
                        "bullet_updates": bullet_updates,
                        "keyword_updates": keyword_updates,
                    },
                    "message": f"{agent_name} agent passed quality gate",
                }
            )

            await asyncio.sleep(0.3)

            # AGENT_COMPLETE
            await websocket.send_json(
                {
                    "event_type": "AGENT_COMPLETE",
                    "agent_id": agent_id,
                    "timestamp": time.time(),
                    "data": {},
                    "message": f"{agent_name} agent completed",
                }
            )

        # PIPELINE_COMPLETE
        final_metrics = MOCK_METRICS_PER_AGENT["A_tail"]
        await websocket.send_json(
            {
                "event_type": "PIPELINE_COMPLETE",
                "agent_id": None,
                "timestamp": time.time(),
                "data": {
                    "metrics": final_metrics,
                    "version_id": f"v{int(time.time())}",
                },
                "message": "Pipeline completed successfully",
            }
        )

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json(
                {
                    "event_type": "PIPELINE_ERROR",
                    "agent_id": None,
                    "timestamp": time.time(),
                    "data": {"error_code": "INTERNAL", "message": str(e)},
                    "message": f"Pipeline error: {e}",
                }
            )
        except Exception:
            pass
