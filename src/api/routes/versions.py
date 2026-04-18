"""Temporal Versioning API — Snapshot, diff, and revert canvas versions.

Snapshots are stored in-memory keyed by job_id. Each accept/reject action on
the canvas should call POST /versions/{job_id}/snapshot. The diff endpoint
uses difflib.unified_diff for character-level comparison between two snapshots.
"""

from __future__ import annotations

import difflib
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/versions", tags=["versions"])

# In-memory snapshot store: job_id → list of snapshots
_snapshots: dict[str, list[dict[str, Any]]] = {}


# ------------------------------------------------------------------
# Schemas
# ------------------------------------------------------------------

class SnapshotRequest(BaseModel):
    content: str          # full resume markdown text
    label: str = ""       # e.g. "Accepted bullet b3"
    source: str = "canvas"  # "canvas" | "agent" | "user_edit"


class DiffToken(BaseModel):
    type: str   # "add" | "remove" | "same"
    text: str


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@router.post("/{job_id}/snapshot")
async def create_snapshot(job_id: str, req: SnapshotRequest) -> dict:
    """Save a named snapshot of the current resume state."""
    if job_id not in _snapshots:
        _snapshots[job_id] = []

    snapshot = {
        "id": str(uuid.uuid4()),
        "version_num": len(_snapshots[job_id]) + 1,
        "content": req.content,
        "label": req.label or f"Version {len(_snapshots[job_id]) + 1}",
        "source": req.source,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _snapshots[job_id].append(snapshot)

    logger.info("versions.snapshot_created", job_id=job_id, version=snapshot["version_num"])
    return {"status": "ok", "data": {k: v for k, v in snapshot.items() if k != "content"}}


@router.get("/{job_id}")
async def list_snapshots(job_id: str) -> dict:
    """Return ordered list of snapshots (metadata only, no content)."""
    snaps = _snapshots.get(job_id, [])
    return {
        "status": "ok",
        "data": {
            "snapshots": [
                {k: v for k, v in s.items() if k != "content"}
                for s in snaps
            ],
            "count": len(snaps),
        },
    }


@router.get("/{job_id}/diff")
async def get_diff(job_id: str, v1_id: str, v2_id: str) -> dict:
    """Return token-level diff between two snapshots.

    Tokens are typed as "add" | "remove" | "same" so the frontend
    can render colored inline diff without processing.
    """
    snaps = _snapshots.get(job_id, [])
    snap_map = {s["id"]: s for s in snaps}

    if v1_id not in snap_map:
        raise HTTPException(404, f"Snapshot {v1_id} not found")
    if v2_id not in snap_map:
        raise HTTPException(404, f"Snapshot {v2_id} not found")

    v1_lines = snap_map[v1_id]["content"].splitlines(keepends=True)
    v2_lines = snap_map[v2_id]["content"].splitlines(keepends=True)

    tokens: list[dict] = []
    matcher = difflib.SequenceMatcher(None, v1_lines, v2_lines)
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == "equal":
            for line in v1_lines[i1:i2]:
                tokens.append({"type": "same", "text": line})
        elif op in ("replace", "delete"):
            for line in v1_lines[i1:i2]:
                tokens.append({"type": "remove", "text": line})
            if op == "replace":
                for line in v2_lines[j1:j2]:
                    tokens.append({"type": "add", "text": line})
        elif op == "insert":
            for line in v2_lines[j1:j2]:
                tokens.append({"type": "add", "text": line})

    return {
        "status": "ok",
        "data": {
            "v1_id": v1_id,
            "v2_id": v2_id,
            "tokens": tokens,
            "additions": sum(1 for t in tokens if t["type"] == "add"),
            "removals":  sum(1 for t in tokens if t["type"] == "remove"),
        },
    }


@router.post("/{job_id}/revert")
async def revert_to_snapshot(job_id: str, version_id: str) -> dict:
    """Restore canvas to a previous snapshot state."""
    snaps = _snapshots.get(job_id, [])
    snap_map = {s["id"]: s for s in snaps}

    if version_id not in snap_map:
        raise HTTPException(404, f"Snapshot {version_id} not found")

    snap = snap_map[version_id]

    # Create a new snapshot that is a copy of the reverted state
    reverted = {
        "id": str(uuid.uuid4()),
        "version_num": len(snaps) + 1,
        "content": snap["content"],
        "label": f"Reverted to: {snap['label']}",
        "source": "revert",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _snapshots[job_id].append(reverted)

    logger.info("versions.reverted", job_id=job_id, to_version=snap["version_num"])
    return {
        "status": "ok",
        "data": {
            "reverted_to": version_id,
            "new_snapshot_id": reverted["id"],
            "content": reverted["content"],
        },
    }
