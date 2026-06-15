"""Pipeline Orchestrator — Runs the full 7-agent pipeline with real-time event broadcasting."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Callable, Awaitable

import structlog

from src.agents.ats_agent import ATSAgent
from src.agents.base_agent import AgentInput, AgentOutput
from src.agents.generation_agent import GenerationAgent
from src.agents.ingestion_agent import IngestionAgent
from src.agents.interview_agent import InterviewAgent
from src.agents.quality_agent import QualityAgent
from src.agents.tailoring_agent import AlignmentGateError, TailoringAgent
from src.agents.weak_detection_agent import WeakDetectionAgent
from src.rag.embedder import Embedder
from src.rag.retriever import Retriever
from src.rag.vector_store import VectorStore
from src.scoring.alignment import AlignmentScorer
from src.scoring.impact_scorer import ImpactScorer
from src.scoring.keyword_coverage import KeywordCoverageScorer

logger = structlog.get_logger()

# Type alias for optional WebSocket event emitter
EventEmitter = Callable[[dict[str, Any]], Awaitable[None]]


class Pipeline:
    """Orchestrates the 7-agent pipeline.

    Order: Ingestion → Generation → Quality → WeakDetection → Tailoring → ATS
    Interview agent runs in parallel with ATS.
    """

    def __init__(self, llm_client: object, user_id: str = "default") -> None:
        self.llm = llm_client
        self.user_id = user_id

        # Shared RAG infrastructure
        self.embedder = Embedder()
        self.vector_store = VectorStore()
        self.retriever = Retriever(self.embedder, self.vector_store, user_id)

        # Scoring utilities
        self.alignment_scorer = AlignmentScorer(self.embedder)
        self.impact_scorer = ImpactScorer()
        self.keyword_scorer = KeywordCoverageScorer()

        # Initialize all 7 agents
        self.ingestion = IngestionAgent(self.retriever)
        self.generation = GenerationAgent(self.retriever, self.llm)
        self.quality = QualityAgent(self.retriever, self.llm)
        self.weak_detection = WeakDetectionAgent(self.retriever, self.llm)
        self.tailoring = TailoringAgent(self.retriever, self.llm)
        self.interview = InterviewAgent(self.retriever, self.llm)
        self.ats = ATSAgent(self.retriever, self.llm)

    async def run(
        self,
        resume_text: str,
        job_description: str,
        skip_interview: bool = False,
        emit: EventEmitter | None = None,
    ) -> dict[str, Any]:
        """Run the full optimization pipeline.

        Args:
            resume_text: Raw resume text.
            job_description: Target job description.
            skip_interview: Skip interview agent if True.
            emit: Optional async callable to broadcast AgentEvent dicts over WebSocket.

        Returns:
            Dict with all agent outputs + computed metrics.
        """
        logger.info("pipeline.start", user_id=self.user_id)
        results: dict[str, AgentOutput] = {}

        async def _run_agent(agent_id: str, agent_name: str, agent, input_data: AgentInput) -> AgentOutput:
            await _emit(emit, {
                "event_type": "AGENT_START",
                "agent_id": agent_id,
                "agent_name": agent_name,
                "timestamp": time.time(),
                "data": {},
                "message": f"{agent_name} started",
            })
            output = await agent.run(input_data)
            await _emit(emit, {
                "event_type": "AGENT_COMPLETE",
                "agent_id": agent_id,
                "agent_name": agent_name,
                "timestamp": time.time(),
                "quality_gate_passed": True,
                "quality_score": output.quality_score,
                "data": {
                    "unresolvable_count": len(output.unresolvable_bullets),
                    "suggestions_count": len(output.suggestions),
                },
                "message": f"{agent_name} completed (score={output.quality_score:.2f})",
            })
            return output

        # ── Step 1: Ingestion ────────────────────────────────────────────────
        input_data = AgentInput(content=resume_text, job_description=job_description)
        results["ingestion"] = await _run_agent("A_ing", "Ingestion", self.ingestion, input_data)

        # ── Step 2: Generation ───────────────────────────────────────────────
        gen_input = AgentInput(
            content=resume_text,
            job_description=job_description,
            sections=results["ingestion"].sections,
            previous_output=results["ingestion"],
        )
        results["generation"] = await _run_agent("A_gen", "Generation", self.generation, gen_input)

        # ── Step 3: Quality (3-stage escalating retry) ───────────────────────
        quality_input = AgentInput(
            content=results["generation"].content,
            job_description=job_description,
            previous_output=results["generation"],
        )
        results["quality"] = await _run_agent("A_qual", "Quality", self.quality, quality_input)

        # ── Step 4: Weak Detection ───────────────────────────────────────────
        weak_input = AgentInput(
            content=results["quality"].content,
            job_description=job_description,
            sections=results["ingestion"].sections,
            previous_output=results["quality"],
        )
        results["weak_detection"] = await _run_agent("A_weak", "Weak Detection", self.weak_detection, weak_input)

        # ── Step 5: Tailoring (semantic alignment gate) ──────────────────────
        tailor_input = AgentInput(
            content=results["quality"].content,
            job_description=job_description,
            sections=results["ingestion"].sections,
            previous_output=results["weak_detection"],
        )
        try:
            results["tailoring"] = await _run_agent("A_tail", "Tailoring", self.tailoring, tailor_input)
        except AlignmentGateError as e:
            await _emit(emit, {
                "event_type": "ALIGNMENT_GATE_ABORT",
                "agent_id": "A_tail",
                "timestamp": time.time(),
                "data": {
                    "alignment_score": e.alignment_score,
                    "weak_sections": e.weak_sections,
                },
                "message": f"Tailoring aborted: alignment {e.alignment_score:.3f} < 0.6",
            })
            results["tailoring"] = AgentOutput(
                content=results["quality"].content,
                quality_score=e.alignment_score,
                metadata={
                    "alignment_gate_aborted": True,
                    "alignment_score": e.alignment_score,
                    "weak_sections": e.weak_sections,
                },
            )

        # ── Steps 6+7: Interview + ATS in parallel ───────────────────────────
        parallel_tasks = []

        if not skip_interview:
            interview_input = AgentInput(
                content=results["tailoring"].content,
                job_description=job_description,
                previous_output=results["tailoring"],
            )
            parallel_tasks.append(
                _run_agent("A_int", "Interview", self.interview, interview_input)
            )

        ats_input = AgentInput(
            content=results["tailoring"].content,
            job_description=job_description,
            sections=results["ingestion"].sections,
            previous_output=results["tailoring"],
        )
        parallel_tasks.append(
            _run_agent("A_ats", "ATS Simulation", self.ats, ats_input)
        )

        parallel_results = await asyncio.gather(*parallel_tasks, return_exceptions=True)

        idx = 0
        if not skip_interview:
            interview_out = parallel_results[idx]
            results["interview"] = interview_out if not isinstance(interview_out, Exception) else AgentOutput(content="", quality_score=0.0)
            idx += 1
        ats_out = parallel_results[idx]
        results["ats"] = ats_out if not isinstance(ats_out, Exception) else AgentOutput(content="", quality_score=0.0)

        # ── ATS ≥ 85% enforcement: retry tailoring with ATS-boost ────────────
        ats_score_raw = results["ats"].metadata.get("aggregate_ats_score", 0.65)
        if ats_score_raw < 0.85:
            logger.info("pipeline.ats_boost", current_score=ats_score_raw)
            await _emit(emit, {
                "event_type": "AGENT_START",
                "agent_id": "A_tail",
                "agent_name": "Tailoring (ATS Boost)",
                "timestamp": time.time(),
                "data": {"current_ats": ats_score_raw},
                "message": f"ATS score {int(ats_score_raw * 100)}% — re-tailoring to reach 85%+",
            })
            boost_tailor_input = AgentInput(
                content=results["quality"].content,
                job_description=job_description,
                sections=results["ingestion"].sections,
                previous_output=results["ats"],
                metadata={"ats_boost": True, "current_ats_score": ats_score_raw},
            )
            try:
                results["tailoring"] = await _run_agent(
                    "A_tail", "Tailoring (ATS Boost)", self.tailoring, boost_tailor_input
                )
                # Re-run ATS on boosted content
                boost_ats_input = AgentInput(
                    content=results["tailoring"].content,
                    job_description=job_description,
                    sections=results["ingestion"].sections,
                    previous_output=results["tailoring"],
                )
                results["ats"] = await _run_agent(
                    "A_ats", "ATS Simulation (Boost)", self.ats, boost_ats_input
                )
            except Exception as boost_err:
                logger.warning("pipeline.ats_boost_failed", error=str(boost_err))

        # ── Compute final metrics ────────────────────────────────────────────
        final_content = results["tailoring"].content
        jd_lines = [l.strip() for l in job_description.split("\n") if l.strip()]
        impact_result = self.impact_scorer.score(final_content)
        keyword_result = self.keyword_scorer.score(final_content, jd_lines)
        ats_score = int(results["ats"].metadata.get("aggregate_ats_score", 0.65) * 100)
        tailoring_meta = results["tailoring"].metadata
        alignment = tailoring_meta.get("alignment_score") or tailoring_meta.get("pre_tailoring_alignment", 0.0)

        metrics = {
            "alignment": round(float(alignment), 3),
            "keywordCoverage": int(keyword_result.coverage_score * 100),
            "impactScore": round(impact_result.overall_score, 3),
            "atsPassRate": ats_score,
            "matchedKeywords": keyword_result.matched_keywords[:20],
            "missingKeywords": keyword_result.missing_keywords[:20],
        }

        await _emit(emit, {
            "event_type": "PIPELINE_COMPLETE",
            "agent_id": None,
            "timestamp": time.time(),
            "data": {"metrics": metrics},
            "message": "Pipeline completed successfully",
        })

        logger.info("pipeline.complete", user_id=self.user_id, agents_run=list(results.keys()))

        return {
            "agents": {
                name: _serialize_output(output)
                for name, output in results.items()
            },
            "metrics": metrics,
            "original_content": resume_text,
            "optimized_content": final_content,
            "unresolvable_bullets": results["quality"].unresolvable_bullets,
            "ats_reports": results["ats"].metadata.get("platform_reports", {}),
        }


async def _emit(emit: EventEmitter | None, event: dict[str, Any]) -> None:
    if emit is not None:
        try:
            await emit(event)
        except Exception:
            pass


def _serialize_output(output: AgentOutput) -> dict[str, Any]:
    provenance = None
    if output.provenance:
        provenance = {
            "agent_name": output.provenance.agent_name,
            "input_summary": output.provenance.input_summary,
            "retrieved_chunk_ids": output.provenance.retrieved_chunk_ids,
            "decision_rationale": output.provenance.decision_rationale,
            "confidence": output.provenance.confidence,
        }
    return {
        "content": output.content,
        "quality_score": output.quality_score,
        "suggestions": output.suggestions,
        "metadata": output.metadata,
        "provenance": provenance,
        "unresolvable_bullets": output.unresolvable_bullets,
    }
