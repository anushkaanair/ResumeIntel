"""Collaborative Review routes — shared canvas sessions with mentor annotations.

Flow:
  POST /collab/sessions               — create session, get shared_token
  GET  /collab/{token}/annotations/{bullet_id} — fetch annotations for a bullet
  POST /collab/{token}/annotations    — add a mentor/AI annotation
  GET  /collab/{token}/session        — get session metadata
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/collab", tags=["collab"])

# In-memory store (replace with DB once auth system is complete)
_sessions: dict[str, dict] = {}                         # token → session
_annotations: dict[str, list[dict]] = {}                # token → [annotation, ...]


class CreateSessionRequest(BaseModel):
    job_id: str
    owner_id: str = "owner"


class AnnotationRequest(BaseModel):
    bullet_id: str
    author_id: str = "guest"
    source: str = "mentor"    # 'mentor' | 'ai'
    text: str


@router.post("/sessions")
async def create_session(req: CreateSessionRequest) -> dict:
    """Create a collaborative review session and return a shareable token."""
    token = str(uuid.uuid4())
    _sessions[token] = {
        "id":           str(uuid.uuid4()),
        "job_id":       req.job_id,
        "owner_id":     req.owner_id,
        "shared_token": token,
        "created_at":   datetime.now(timezone.utc).isoformat(),
    }
    _annotations[token] = []
    logger.info("collab.session_created", job_id=req.job_id, token=token)
    return {"status": "ok", "data": {"shared_token": token, "session": _sessions[token]}}


@router.get("/{token}/session")
async def get_session(token: str) -> dict:
    if token not in _sessions:
        raise HTTPException(404, "Session not found")
    return {"status": "ok", "data": {"session": _sessions[token]}}


@router.get("/{token}/annotations/{bullet_id}")
async def get_annotations(token: str, bullet_id: str) -> dict:
    if token not in _sessions:
        raise HTTPException(404, "Session not found")
    anns = [a for a in _annotations.get(token, []) if a["bullet_id"] == bullet_id]
    return {"status": "ok", "data": {"annotations": anns}}


@router.post("/{token}/annotations")
async def add_annotation(token: str, req: AnnotationRequest) -> dict:
    if token not in _sessions:
        raise HTTPException(404, "Session not found")

    annotation = {
        "id":         str(uuid.uuid4()),
        "bullet_id":  req.bullet_id,
        "author_id":  req.author_id,
        "source":     req.source,
        "text":       req.text,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _annotations.setdefault(token, []).append(annotation)
    logger.info("collab.annotation_added", token=token, bullet_id=req.bullet_id, source=req.source)
    return {"status": "ok", "data": {"annotation": annotation}}
