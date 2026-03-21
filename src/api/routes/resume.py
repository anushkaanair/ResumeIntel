"""Resume upload and management routes."""

from __future__ import annotations

from fastapi import APIRouter, File, UploadFile

from src.api.schemas.resume import ResumeUploadResponse
from src.parsers.resume_parser import ResumeParser

router = APIRouter()
parser = ResumeParser()


@router.post("/resume/upload", response_model=ResumeUploadResponse)
async def upload_resume(file: UploadFile = File(...)) -> ResumeUploadResponse:
    """Upload and parse a resume file (PDF, DOCX, TXT)."""
    content = await file.read()
    import io

    text = parser.parse(io.BytesIO(content), file.filename or "resume.txt")

    return ResumeUploadResponse(
        status="ok",
        data={"text": text, "filename": file.filename, "chars": len(text)},
    )
