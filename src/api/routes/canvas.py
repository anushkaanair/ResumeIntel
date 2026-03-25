"""Canvas API routes — bullet scoring, AI suggestions, accept/reject, export.

These are mock/demo routes that return realistic data shapes matching the V2 spec.
They allow the frontend to be fully functional and visually dynamic without
requiring actual LLM processing or database state.
"""
from __future__ import annotations

import random
import uuid

from fastapi import APIRouter  # type: ignore
from pydantic import BaseModel, Field  # type: ignore

router = APIRouter()


# ─── Schemas ─────────────────────────────────────────────


class BulletScoreRequest(BaseModel):
    text: str = Field(..., min_length=5)


class BulletScoreResponse(BaseModel):
    impact_score: float
    alignment_delta: float


class BulletSuggestRequest(BaseModel):
    text: str = Field(..., min_length=5)
    jd_id: str | None = None


class BulletSuggestResponse(BaseModel):
    suggestion: str
    rationale: str


class BulletAcceptRequest(BaseModel):
    version: str = Field(..., description="'ai' | 'user' | 'original'")


class BulletAcceptResponse(BaseModel):
    updated_bullet: dict


class SectionReoptimizeRequest(BaseModel):
    section_id: str
    section_title: str


class SectionEnhanceRequest(BaseModel):
    section_id: str
    section_title: str
    prompt: str


class ProfileRefreshRequest(BaseModel):
    profile_type: str = Field(description="'linkedin' | 'github'")



# ─── Mock canvas state ──────────────────────────────────

MOCK_METRICS = {
    "alignment": 0.68,
    "keywordCoverage": 70,
    "impactScore": 0.61,
    "atsPassRate": 65,
}


@router.get("/canvas/{resume_id}/state")
async def get_canvas_state(resume_id: str) -> dict:
    """Return full canvas state for initial page load."""
    return {
        "status": "ok",
        "data": {
            "resume": {
                "id": resume_id,
                "header": {
                    "name": "Alex Morgan",
                    "email": "alex.morgan@email.com",
                    "phone": "+1 (555) 012-3456",
                    "location": "San Francisco, CA",
                    "linkedin": "linkedin.com/in/alexmorgan",
                    "github": "github.com/amorgan",
                },
                "sections": [
                    {
                        "id": "sec-summary",
                        "type": "summary",
                        "title": "Professional Summary",
                        "position": 0,
                        "content": {
                            "text": "Full-stack engineer with 5+ years of experience "
                            "building scalable SaaS platforms."
                        },
                    },
                    {
                        "id": "sec-exp",
                        "type": "experience",
                        "title": "Experience",
                        "position": 1,
                        "content": {
                            "entries": [
                                {
                                    "company": "TechCorp Inc.",
                                    "title": "Senior Software Engineer",
                                    "startDate": "2022-01",
                                    "endDate": "Present",
                                    "bullets": [
                                        {
                                            "id": "b1",
                                            "originalText": "Led development of microservices",
                                            "currentText": "Led development of microservices",
                                            "aiSuggestion": None,
                                            "impactScore": 0.82,
                                            "status": "original",
                                        }
                                    ],
                                }
                            ]
                        },
                    },
                ],
                "currentVersion": 1,
                "versions": [
                    {
                        "id": "v1",
                        "versionNum": 1,
                        "label": "Uploaded",
                        "timestamp": "2026-03-24T12:00:00Z",
                        "source": "USER_EDIT",
                    }
                ],
            },
            "metrics": MOCK_METRICS,
            "jd": None,
            "pipeline": {
                "agents": {
                    "A_ing": "idle",
                    "A_gen": "idle",
                    "A_qual": "idle",
                    "A_weak": "idle",
                    "A_tail": "idle",
                    "A_int": "idle",
                },
                "currentAgent": None,
                "isRunning": False,
            },
        },
    }


@router.post("/canvas/bullet/{bullet_id}/score")
async def score_bullet(bullet_id: str, request: BulletScoreRequest) -> dict:
    """Lightweight single-bullet scoring. Returns impact score + alignment delta."""
    # Simulate scoring based on text heuristics
    text = request.text.lower()
    has_metric = any(c.isdigit() for c in text)
    has_action_verb = any(
        v in text
        for v in [
            "led",
            "built",
            "designed",
            "developed",
            "optimized",
            "implemented",
            "architected",
            "delivered",
            "reduced",
            "increased",
        ]
    )
    has_outcome = any(w in text for w in ["%", "revenue", "users", "latency", "uptime", "reduced", "improved"])

    score = 0.3 + (0.2 if has_metric else 0) + (0.2 if has_action_verb else 0) + (0.2 if has_outcome else 0)
    score = min(score + random.uniform(-0.05, 0.1), 1.0)

    return {
        "status": "ok",
        "data": {
            "impact_score": round(score, 3),  # type: ignore
            "alignment_delta": round(random.uniform(-0.02, 0.05), 3),  # type: ignore
        },
    }


@router.post("/canvas/bullet/{bullet_id}/suggest")
async def suggest_bullet(bullet_id: str, request: BulletSuggestRequest) -> dict:
    """Generate an AI improvement suggestion for an edited bullet."""
    text = request.text

    # Simple mock transformation
    improvements = [
        f"Spearheaded {text.lower()}, driving measurable impact across cross-functional teams",
        f"Engineered and deployed {text.lower()}, achieving 40% performance improvement",
        f"Led initiative to {text.lower()}, resulting in $500K annual cost savings",
    ]

    suggestion = random.choice(improvements)

    return {
        "status": "ok",
        "data": {
            "suggestion": suggestion,
            "rationale": "Enhanced with action verb, quantifiable metric, and outcome statement.",
        },
    }


@router.post("/canvas/bullet/{bullet_id}/accept")
async def accept_bullet(bullet_id: str, request: BulletAcceptRequest) -> dict:
    """Accept AI suggestion, keep user edit, or revert to original."""
    return {
        "status": "ok",
        "data": {
            "updated_bullet": {
                "id": bullet_id,
                "status": "accepted" if request.version == "ai" else ("user_edited" if request.version == "user" else "original"),
            }
        },
    }


@router.get("/canvas/{resume_id}/export/pdf")
async def export_canvas_pdf(resume_id: str):
    """Generate and download resume PDF. (Mock — returns placeholder.)"""
    from fastapi.responses import Response  # type: ignore

    # In production, this would use WeasyPrint to render HTML→PDF
    placeholder = f"PDF export for resume {resume_id} (mock placeholder)"
    return Response(
        content=placeholder.encode(),
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="resume_{resume_id}.txt"'},
    )


@router.post("/canvas/section/{section_id}/reoptimize")
async def reoptimize_section(section_id: str, request: SectionReoptimizeRequest) -> dict:
    """Mock re-optimization of an entire section."""
    return {
        "status": "ok",
        "data": {
            "message": f"{request.section_title} partially re-optimized by AI",
            "section_id": section_id,
        }
    }


@router.post("/canvas/section/{section_id}/enhance")
async def enhance_section(section_id: str, request: SectionEnhanceRequest) -> dict:
    """Mock manual AI enhancement of a section."""
    return {
        "status": "ok",
        "data": {
            "message": f"{request.section_title} enhanced based on prompt: {request.prompt[:20]}...",  # type: ignore
            "section_id": section_id,
        }
    }


@router.post("/canvas/profile/linkedin/refresh")
async def refresh_linkedin() -> dict:
    """Mock LinkedIn profile refresh."""
    has_changes = random.random() > 0.5
    items = ["Updated headline: 'Senior Full-Stack Engineer'", "Added new certification: AWS Solutions Architect"] if has_changes else []
    return {
        "status": "ok",
        "data": {
            "has_changes": has_changes,
            "items": items,
        }
    }


@router.post("/canvas/profile/github/refresh")
async def refresh_github() -> dict:
    """Mock GitHub profile refresh."""
    has_changes = random.random() > 0.5
    items = ["3 new commits to ai-resume-system", "New repo created: portfolio-v2"] if has_changes else []
    return {
        "status": "ok",
        "data": {
            "has_changes": has_changes,
            "items": items,
        }
    }

