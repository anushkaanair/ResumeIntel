"""Interview Agent — Generates interview preparation materials from optimized resume."""

from __future__ import annotations

import structlog

from src.agents.base_agent import AgentInput, AgentOutput, BaseAgent
from src.exceptions import QualityGateError
from src.rag.retriever import Retriever

logger = structlog.get_logger()


class InterviewAgent(BaseAgent):
    """Generates interview prep questions and talking points based on resume + JD."""

    QUALITY_THRESHOLD = 0.6
    MAX_RETRIES = 3

    def __init__(self, retriever: Retriever, llm_client: object) -> None:
        self.retriever = retriever
        self.llm = llm_client

    async def execute(self, input: AgentInput) -> AgentOutput:
        # RAG: retrieve experience segments for interview prep
        context = await self.retriever.retrieve(
            query=f"interview questions for {input.job_description[:200]}",
            top_k=10,
        )

        prompt = self._build_prompt(input, context)
        prep_material = await self.llm.generate(prompt)

        return AgentOutput(
            content=prep_material,
            quality_score=self._score_prep(prep_material),
            sources=context,
            metadata={"type": "interview_prep"},
        )

    def validate_input(self, input: AgentInput) -> None:
        if not input.content:
            raise ValueError("No resume content for interview prep")

    def validate_output(self, output: AgentOutput) -> None:
        if output.quality_score < self.QUALITY_THRESHOLD:
            raise QualityGateError(
                f"Interview prep quality {output.quality_score:.2f} below threshold"
            )

    def _build_prompt(self, input: AgentInput, context: list) -> str:
        context_text = "\n".join(f"- {seg.content}" for seg in context)

        return f"""You are an expert interview coach and technical recruiter who has conducted 1000+ technical and behavioral interviews.
Your task is to generate targeted interview preparation material grounded entirely in the candidate's actual resume.

STRICT RULES:
- Use ONLY experiences, skills, metrics, and achievements found in the resume — do not invent stories or outcomes.
- Every behavioral answer framework must cite a specific experience from the resume.
- STAR = Situation, Task, Action, Result. Be specific at each step.
- Technical questions must match the actual tech stack and seniority implied by the resume.

CANDIDATE RESUME:
{input.content[:3000]}

TARGET JOB DESCRIPTION:
{input.job_description or "General software engineering role — focus on technical and behavioral breadth"}

HIGH-RELEVANCE EXPERIENCE SEGMENTS (from RAG):
{context_text}

OUTPUT FORMAT — use this exact structure:

## Behavioral Questions
For each question, include the question and a STAR framework outline using resume evidence.
Format:
**Q1: [Question]**
- Situation: [from resume]
- Task: [what was needed]
- Action: [what candidate did — use resume verbs/details]
- Result: [outcome with metric if available]

Generate 5–7 behavioral questions targeting: leadership, conflict resolution, technical decision-making, handling failure, and collaboration.

## Technical Questions
5–7 questions testing the specific technologies, patterns, and seniority level evident in the resume and required by the JD.
Include a brief ideal answer note for each question.
Format: **Q1: [Question]** → Key points to cover: ...

## Talking Points
3–5 high-impact achievements the candidate should proactively mention. Each must include:
- The achievement headline (with metric where available from resume)
- Why it's relevant to this specific JD
- One-sentence delivery suggestion

## Questions to Ask the Interviewer
3–5 thoughtful, role-specific questions the candidate can ask. Tailor these to the JD — avoid generic questions.

Be specific and actionable throughout. Vague advice like "talk about your experience" is not acceptable."""

    def _score_prep(self, content: str) -> float:
        """Score interview prep completeness."""
        if not content.strip():
            return 0.0

        score = 0.4
        lower = content.lower()

        if "behavioral" in lower or "star" in lower:
            score += 0.15
        if "technical" in lower:
            score += 0.15
        if "talking point" in lower:
            score += 0.15
        if "questions to ask" in lower or "ask the interviewer" in lower:
            score += 0.15

        return min(score, 1.0)
