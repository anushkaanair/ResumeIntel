"""Pydantic models for job description schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class JobDescriptionInput(BaseModel):
    text: str = Field(..., min_length=20, description="Job description text")
    title: str | None = None
    company: str | None = None


class JobAnalysisResponse(BaseModel):
    status: str = "ok"
    data: dict = Field(default_factory=dict)
    meta: dict | None = None
