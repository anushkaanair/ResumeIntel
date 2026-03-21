"""Export routes — placeholder for resume export functionality."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.post("/export/pdf")
async def export_pdf() -> dict:
    """Export optimized resume as PDF."""
    # TODO: implement PDF export
    return {"status": "ok", "data": {"message": "PDF export not yet implemented"}}


@router.post("/export/docx")
async def export_docx() -> dict:
    """Export optimized resume as DOCX."""
    # TODO: implement DOCX export
    return {"status": "ok", "data": {"message": "DOCX export not yet implemented"}}
