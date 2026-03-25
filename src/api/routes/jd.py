"""JD (Job Description) parsing and retrieval routes — real JDParser, Redis-backed."""

from __future__ import annotations

import uuid

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.db.redis_store import rget, rset
from src.parsers.jd_parser import JDParser

router = APIRouter()

_JD_KEY = "jd:{jd_id}"


class JDParseRequest(BaseModel):
    raw_text: str = Field(..., min_length=20)
    url: str | None = None


@router.post("/jd/parse")
async def parse_jd(request: JDParseRequest) -> dict:
    """Parse and analyze a job description using JDParser."""
    parser = JDParser()
    parsed = parser.parse(request.raw_text)
    jd_id = str(uuid.uuid4())

    data = {
        "id": jd_id,
        "rawText": parsed.raw_text,
        "title": parsed.title,
        "company": parsed.company,
        "keywords": parsed.keywords,
        "requirements": parsed.requirements,
        "responsibilities": parsed.responsibilities,
        "qualifications": parsed.qualifications,
        "skills": parsed.skills,
    }

    await rset(_JD_KEY.format(jd_id=jd_id), data)
    return {"status": "ok", "data": data}


@router.get("/jd/{jd_id}")
async def get_jd(jd_id: str) -> dict:
    """Fetch a parsed JD by ID."""
    data = await rget(_JD_KEY.format(jd_id=jd_id))
    if not data:
        return {
            "status": "error",
            "error": {"code": "NOT_FOUND", "message": f"JD {jd_id} not found"},
        }
    return {"status": "ok", "data": data}
