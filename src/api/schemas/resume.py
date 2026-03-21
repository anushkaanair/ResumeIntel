"""Pydantic models for resume-related API schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ResumeUploadResponse(BaseModel):
    status: str = "ok"
    data: dict = Field(default_factory=dict)
    meta: dict | None = None


class OptimizeRequest(BaseModel):
    resume_text: str = Field(..., min_length=50, description="Resume content text")
    job_description: str = Field(..., min_length=20, description="Target job description")
    options: OptimizeOptions | None = None


class OptimizeOptions(BaseModel):
    skip_interview_prep: bool = False
    quality_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    max_retries: int = Field(default=3, ge=1, le=5)


class OptimizeResponse(BaseModel):
    status: str = "ok"
    data: dict = Field(default_factory=dict)
    meta: dict | None = None


class OptimizeStatusResponse(BaseModel):
    status: str
    data: dict = Field(default_factory=dict)


class AlignmentScoreRequest(BaseModel):
    resume_text: str = Field(..., min_length=50)
    job_description: str = Field(..., min_length=20)


class AlignmentScoreResponse(BaseModel):
    status: str = "ok"
    data: dict = Field(default_factory=dict)
