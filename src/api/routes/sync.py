"""GitHub/LinkedIn Profile Sync routes.

Flow:
  1. POST /sync/connect          — exchange OAuth code for token (stores encrypted)
  2. GET  /sync/status           — staleness scores + pending delta counts
  3. POST /sync/refresh          — trigger delta fetch for one platform
  4. GET  /sync/deltas           — list pending (unapplied) deltas
  5. POST /sync/apply/{delta_id} — route a delta through Gen+Quality → canvas bullet
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.agents.sync_agent import SyncAgent

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/sync", tags=["sync"])

# ---------------------------------------------------------------------------
# Simple encryption helpers (Fernet when key is set, base64 fallback for dev)
# ---------------------------------------------------------------------------

def _encrypt(token: str) -> str:
    key = os.getenv("TOKEN_ENCRYPTION_KEY", "")
    if key:
        try:
            from cryptography.fernet import Fernet  # type: ignore[import]
            return Fernet(key.encode()).encrypt(token.encode()).decode()
        except Exception:
            pass
    import base64
    return base64.b64encode(token.encode()).decode()


def _decrypt(token: str) -> str:
    key = os.getenv("TOKEN_ENCRYPTION_KEY", "")
    if key:
        try:
            from cryptography.fernet import Fernet  # type: ignore[import]
            return Fernet(key.encode()).decrypt(token.encode()).decode()
        except Exception:
            pass
    import base64
    return base64.b64decode(token.encode()).decode()


# ---------------------------------------------------------------------------
# In-memory stores (replace with DB queries once DB is wired)
# ---------------------------------------------------------------------------

_sync_states: dict[str, dict[str, Any]] = {}   # user_id → {platform → state}
_sync_deltas: dict[str, list[dict]]      = {}   # user_id → [delta, ...]

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ConnectRequest(BaseModel):
    platform: str   # 'github' | 'linkedin'
    access_token: str  # pre-obtained OAuth token from the client-side OAuth flow


class ApplyDeltaRequest(BaseModel):
    job_id: str
    user_id: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/connect")
async def connect_platform(req: ConnectRequest, user_id: str = "demo-user") -> dict:
    """Store an OAuth access token for a platform.

    In production, exchange an OAuth code here.
    For now, accept a pre-obtained token directly.
    Returns 501 when the relevant OAuth client ID is not configured in .env.
    """
    if req.platform == "github" and not os.getenv("GITHUB_CLIENT_ID"):
        raise HTTPException(
            501,
            "GitHub OAuth not configured. Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET in .env",
        )
    if req.platform == "linkedin" and not os.getenv("LINKEDIN_CLIENT_ID"):
        raise HTTPException(
            501,
            "LinkedIn OAuth not configured. Set LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET in .env",
        )

    _sync_states.setdefault(user_id, {})
    _sync_states[user_id][req.platform] = {
        "platform":       req.platform,
        "access_token":   _encrypt(req.access_token),
        "last_sync_at":   None,
        "sync_cursor":    None,
        "staleness_score": 1.0,
    }
    logger.info("sync.platform_connected", user_id=user_id, platform=req.platform)
    return {"status": "ok", "data": {"platform": req.platform, "connected": True}}


@router.get("/status")
async def get_sync_status(user_id: str = "demo-user") -> dict:
    """Return staleness scores and pending delta counts per platform."""
    states = _sync_states.get(user_id, {})
    pending_by_platform: dict[str, int] = {}
    for delta in _sync_deltas.get(user_id, []):
        if not delta.get("applied"):
            plat = delta["platform"]
            pending_by_platform[plat] = pending_by_platform.get(plat, 0) + 1

    return {
        "status": "ok",
        "data": {
            "platforms": [
                {
                    "platform":       p,
                    "last_sync_at":   s.get("last_sync_at"),
                    "staleness_score": s.get("staleness_score", 1.0),
                    "pending_deltas": pending_by_platform.get(p, 0),
                }
                for p, s in states.items()
            ]
        },
    }


@router.post("/refresh")
async def trigger_refresh(
    platform: str,
    job_id: str,
    user_id: str = "demo-user",
) -> dict:
    """Trigger a delta fetch for one platform, scored against the job's JD."""
    states = _sync_states.get(user_id, {})
    state = states.get(platform)
    if not state:
        raise HTTPException(404, f"Platform '{platform}' not connected for user {user_id}")

    # Load JD from optimize results (in-memory store in optimize.py)
    from src.api.routes.optimize import _results as _opt_results
    job_data = _opt_results.get(job_id, {})
    jd_text = ""
    if job_data.get("results"):
        # Extract JD from any agent result that has it
        for agent_res in job_data["results"].values():
            if isinstance(agent_res, dict) and agent_res.get("metadata", {}).get("job_description"):
                jd_text = agent_res["metadata"]["job_description"]
                break

    from src.rag.embedder import Embedder
    embedder = Embedder()
    jd_embedding = embedder.encode_single(jd_text or platform)

    agent = SyncAgent()
    from src.agents.base_agent import AgentInput
    sync_input = AgentInput(
        content="",
        job_description=jd_text,
        metadata={
            "platform":     platform,
            "access_token": _decrypt(state["access_token"]),
            "sync_cursor":  state.get("sync_cursor"),
            "jd_embedding": jd_embedding,
        },
    )
    result = await agent.execute(sync_input)

    # Persist deltas
    user_deltas = _sync_deltas.setdefault(user_id, [])
    new_deltas = result.metadata.get("deltas", [])
    for delta in new_deltas:
        import uuid
        delta["id"] = str(uuid.uuid4())
        delta["applied"] = False
        delta["detected_at"] = datetime.now(timezone.utc).isoformat()
        user_deltas.append(delta)

    # Update sync state
    state["last_sync_at"] = datetime.now(timezone.utc).isoformat()
    state["sync_cursor"]  = result.metadata.get("new_cursor", state.get("sync_cursor"))
    state["staleness_score"] = 0.0

    logger.info("sync.refresh_complete", user_id=user_id, platform=platform, deltas=len(new_deltas))
    return {"status": "ok", "data": {"deltas_found": len(new_deltas)}}


@router.get("/deltas")
async def get_deltas(user_id: str = "demo-user") -> dict:
    """Return all pending (unapplied) deltas sorted by relevance score."""
    deltas = [
        d for d in _sync_deltas.get(user_id, [])
        if not d.get("applied")
    ]
    deltas.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
    return {"status": "ok", "data": {"deltas": deltas}}


@router.post("/apply/{delta_id}")
async def apply_delta(delta_id: str, req: ApplyDeltaRequest) -> dict:
    """Route a sync delta through GenerationAgent + QualityAgent → return canvas bullet."""
    user_deltas = _sync_deltas.get(req.user_id, [])
    delta = next((d for d in user_deltas if d.get("id") == delta_id), None)
    if not delta:
        raise HTTPException(404, "Delta not found")

    from src.llm.client import LLMClient
    from src.rag.embedder import Embedder
    from src.rag.vector_store import VectorStore
    from src.rag.retriever import Retriever
    from src.agents.generation_agent import GenerationAgent
    from src.agents.quality_agent import QualityAgent
    from src.agents.base_agent import AgentInput

    embedder = Embedder()
    store = VectorStore()
    retriever = Retriever(embedder, store, req.user_id)
    llm = LLMClient()
    gen_agent = GenerationAgent(retriever, llm)
    qual_agent = QualityAgent(retriever, llm)

    gen_input = AgentInput(
        content=delta.get("description", delta.get("title", "")),
        job_description="",
        sections={"content": delta.get("description", "")},
        metadata={
            "target_section":  delta.get("suggested_section", "Experience"),
            "platform_badge":  delta["platform"],
            "escalation_instruction": f"Generate a strong resume bullet from this {delta['platform']} item.",
        },
    )
    gen_output  = await gen_agent.execute(gen_input)
    qual_input  = AgentInput(content=gen_output.content, job_description="")
    qual_output = await qual_agent.execute(qual_input)

    # Mark applied
    delta["applied"]    = True
    delta["applied_at"] = datetime.now(timezone.utc).isoformat()

    bullet_text = qual_output.content.strip().lstrip("-*• ").strip()

    return {
        "status": "ok",
        "data": {
            "bullet":           bullet_text,
            "quality_score":    qual_output.quality_score,
            "platform_badge":   delta["platform"],
            "suggested_section": delta.get("suggested_section", "Experience"),
            "status":           "pending",
        },
    }
