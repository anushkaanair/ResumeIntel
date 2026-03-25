"""Interview API routes — data retrieval, generation trigger, practice mode.

Mock routes that return realistic interview prep data matching the V2 spec.
"""
from __future__ import annotations

import random
import uuid

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()


# ─── Schemas ─────────────────────────────────────────────


class GenerateInterviewRequest(BaseModel):
    resume_id: str
    jd_id: str


class PracticeAnswerRequest(BaseModel):
    user_answer: str = Field(..., min_length=10)


# ─── Mock data ───────────────────────────────────────────

MOCK_GAPS = [
    {
        "id": "g1",
        "type": "missing_skill",
        "severity": "high",
        "description": "No Kubernetes experience mentioned",
        "jdRequirement": "Kubernetes orchestration at scale",
        "suggestedTalkingPoint": "Discuss Docker expertise and eagerness to expand into K8s.",
    },
    {
        "id": "g2",
        "type": "depth_mismatch",
        "severity": "medium",
        "description": "ML experience appears to be 2 years, JD wants 5+",
        "jdRequirement": "5+ years machine learning experience",
        "suggestedTalkingPoint": "Emphasize breadth and impact of your ML work over duration.",
    },
    {
        "id": "g3",
        "type": "missing_domain",
        "severity": "medium",
        "description": "No fintech domain experience visible",
        "jdRequirement": "Experience in financial services or fintech",
        "suggestedTalkingPoint": "Draw parallels between e-commerce and fintech: reliability, transactions, security.",
    },
    {
        "id": "g4",
        "type": "recency_gap",
        "severity": "low",
        "description": "Last GraphQL mention is 3+ years old",
        "jdRequirement": "Strong GraphQL API design skills",
        "suggestedTalkingPoint": "Mention recent GraphQL exposure or ability to ramp quickly.",
    },
]

MOCK_QUESTIONS = [
    {
        "id": "q1",
        "text": "How would you design a scalable microservices architecture for our payment processing platform?",
        "category": "technical",
        "difficulty": "hard",
        "source": "resume_jd_alignment",
        "whyThisQuestion": "Your resume highlights microservices at TechCorp. Interviewer will probe fintech application.",
        "talkingPoints": [
            "Event-driven architecture",
            "Saga pattern for distributed transactions",
            "15K concurrent requests experience",
            "Circuit breakers and fault tolerance",
        ],
        "suggestedStructure": "1. Clarify requirements\n2. High-level architecture\n3. Communication patterns\n4. Data consistency\n5. Monitoring",
    },
    {
        "id": "q2",
        "text": "Tell me about a time you made a difficult technical decision under pressure.",
        "category": "behavioral",
        "difficulty": "medium",
        "source": "common_for_role",
        "whyThisQuestion": "Senior roles require decision-making under uncertainty.",
        "talkingPoints": ["Use STAR format", "Real stakes", "Reasoning process", "Outcome and learning"],
        "suggestedStructure": "1. Situation\n2. Task\n3. Action\n4. Result",
    },
    {
        "id": "q3",
        "text": "What experience do you have with container orchestration tools like Kubernetes?",
        "category": "technical",
        "difficulty": "medium",
        "source": "gap_analysis",
        "whyThisQuestion": "Resume mentions Docker but not Kubernetes — direct gap probe.",
        "talkingPoints": ["Be honest", "Docker as foundation", "Learning initiatives", "Concepts understood"],
        "suggestedStructure": "1. Current level\n2. Transferable skills\n3. Learning plan\n4. Enthusiasm",
    },
    {
        "id": "q4",
        "text": "How would you build a real-time data pipeline for financial transactions?",
        "category": "role_specific",
        "difficulty": "hard",
        "source": "resume_jd_alignment",
        "whyThisQuestion": "Role requires financial data pipeline experience.",
        "talkingPoints": ["Kafka streaming", "Exactly-once semantics", "Compliance/audit", "DB optimization"],
        "suggestedStructure": "1. Requirements\n2. Ingestion\n3. Processing\n4. Storage\n5. Monitoring",
    },
    {
        "id": "q5",
        "text": "What do you know about Acme Corp and why do you want to work here?",
        "category": "company_specific",
        "difficulty": "easy",
        "source": "common_for_role",
        "whyThisQuestion": "Standard company-fit question.",
        "talkingPoints": ["Research company", "Connect mission to interests", "Specific tech excitement"],
        "suggestedStructure": "1. Company knowledge\n2. Experience connection\n3. Enthusiasm",
    },
]


@router.get("/interview/{job_id}")
async def get_interview_data(job_id: str) -> dict:
    """Fetch interview prep data (questions, gaps, talking points)."""
    return {
        "status": "ok",
        "data": {
            "jobId": job_id,
            "resumeId": "mock-resume",
            "jobTitle": "Senior Full-Stack Engineer",
            "company": "Acme Corp",
            "alignmentScore": 0.72,
            "gaps": MOCK_GAPS,
            "questions": MOCK_QUESTIONS,
            "generatedAt": "2026-03-24T12:00:00Z",
        },
    }


@router.post("/interview/{job_id}/generate")
async def generate_interview(job_id: str, request: GenerateInterviewRequest) -> dict:
    """Trigger interview prep generation (mock — returns immediately)."""
    return {
        "status": "ok",
        "data": {"job_id": job_id, "status": "completed"},
    }


@router.post("/interview/question/{question_id}/answer")
async def practice_answer(question_id: str, request: PracticeAnswerRequest) -> dict:
    """Submit a practice answer and receive AI feedback."""
    answer = request.user_answer
    word_count = len(answer.split())

    # Simple heuristic scoring
    base_score = min(45 + word_count, 80)
    has_metrics = any(c.isdigit() for c in answer)
    has_specifics = any(
        w in answer.lower() for w in ["because", "specifically", "example", "result", "achieved", "led"]
    )
    score = min(base_score + (10 if has_metrics else 0) + (8 if has_specifics else 0), 98)

    strengths = [
        "Clear structure in your response",
        "Good use of relevant examples",
    ]
    if has_metrics:
        strengths.append("Effective use of quantifiable metrics")
    if has_specifics:
        strengths.append("Demonstrated specificity and depth")

    improvements = [
        "Consider adding more quantifiable outcomes",
        "Connect your answer more directly to the company's specific needs",
    ]
    if word_count < 80:
        improvements.append("Expand your answer with more detail and examples")
    if not has_metrics:
        improvements.append("Include specific numbers and percentages to strengthen credibility")

    return {
        "status": "ok",
        "data": {
            "score": score,
            "strengths": strengths,
            "improvements": improvements,
            "improved_answer": f"{answer}\n\nAdditionally, these results directly map to the scale "
            "and reliability requirements in the role. Quantifiable impact: "
            "2M+ requests processed daily with 99.97% uptime, while reducing "
            "infrastructure costs by 35%.",
        },
    }
