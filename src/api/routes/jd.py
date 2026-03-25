"""JD (Job Description) parsing and retrieval routes.

Mock routes for parsing and storing job descriptions.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()

# ─── In-memory store ─────────────────────────────────────
_jd_store: dict[str, dict] = {}


class JDParseRequest(BaseModel):
    raw_text: str = Field(None, min_length=20)
    url: str | None = None


@router.post("/jd/parse")
async def parse_jd(request: JDParseRequest) -> dict:
    """Parse and analyze a job description, extracting keywords and requirements."""
    jd_id = str(uuid.uuid4())
    text = request.raw_text or ""

    # Simple keyword extraction (mock)
    tech_keywords = [
        "Python", "React", "TypeScript", "JavaScript", "Node.js",
        "AWS", "Docker", "Kubernetes", "PostgreSQL", "GraphQL",
        "CI/CD", "Microservices", "Redis", "Terraform", "Go",
    ]
    found_keywords = [kw for kw in tech_keywords if kw.lower() in text.lower()]
    if not found_keywords:
        found_keywords = ["Python", "React", "TypeScript", "AWS", "Docker"]

    parsed = {
        "id": jd_id,
        "rawText": text,
        "title": "Senior Full-Stack Engineer",
        "company": "Unknown",
        "location": "Remote",
        "keywords": found_keywords,
        "requirements": [
            "5+ years software engineering experience",
            "Strong proficiency in modern frontend frameworks",
            "Experience with cloud infrastructure",
        ],
        "responsibilities": [
            "Lead architecture decisions for core platform",
            "Mentor junior engineers and conduct code reviews",
        ],
        "qualifications": [
            "Bachelor's or Master's in Computer Science",
        ],
    }

    _jd_store[jd_id] = parsed

    return {"status": "ok", "data": parsed}


@router.get("/jd/{jd_id}")
async def get_jd(jd_id: str) -> dict:
    """Fetch a parsed JD by ID."""
    if jd_id not in _jd_store:
        return {
            "status": "error",
            "error": {"code": "NOT_FOUND", "message": f"JD {jd_id} not found"},
        }
    return {"status": "ok", "data": _jd_store[jd_id]}
