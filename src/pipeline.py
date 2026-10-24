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
from src.config.settings import settings
from src.rag.embedder import Embedder
from src.rag.retriever import Retriever
from src.rag.vector_store import VectorStore
from src.scoring.alignment import AlignmentScorer
from src.scoring.impact_scorer import ImpactScorer
from src.scoring.grounding import check
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
                    # Partial content streamed so the canvas can render incrementally
                    # as each agent finishes, rather than waiting for the full
                    # pipeline to complete (patent claim 12).
                    "content": output.content,
                    "provenance": output.provenance.__dict__ if output.provenance else None,
                },
                "message": f"{agent_name} completed (score={output.quality_score:.2f})",
            })
            return output

        warnings: list[dict[str, str]] = []
        src_meta = {"source_text": resume_text}

        async def _safe(agent_id: str, agent_name: str, agent, input_data: AgentInput, fallback: AgentOutput) -> AgentOutput:
            """Run an agent; on failure keep the pipeline going with `fallback` and record a warning."""
            try:
                return await _run_agent(agent_id, agent_name, agent, input_data)
            except Exception as e:  # noqa: BLE001
                cause = (getattr(e, "context", None) or {}).get("last_error") or str(e)
                logger.warning("pipeline.stage_degraded", agent=agent_name, error=str(cause)[:300])
                warnings.append({"stage": agent_name, "message": str(cause)[:300]})
                await _emit(emit, {
                    "event_type": "AGENT_ERROR",
                    "agent_id": agent_id,
                    "agent_name": agent_name,
                    "timestamp": time.time(),
                    "data": {"error": str(cause)[:300]},
                    "message": f"{agent_name} failed; continuing with the previous version",
                })
                return fallback

        # ── Step 1: Ingestion (a resume we cannot parse is fatal) ────────────
        input_data = AgentInput(content=resume_text, job_description=job_description, metadata=src_meta)
        results["ingestion"] = await _run_agent("A_ing", "Ingestion", self.ingestion, input_data)
        sections = results["ingestion"].sections
        untouched = AgentOutput(content=resume_text, quality_score=0.0, metadata={"degraded": True})

        # ── Step 2: Generation ───────────────────────────────────────────────
        gen_input = AgentInput(
            content=resume_text, job_description=job_description, sections=sections,
            previous_output=results["ingestion"], metadata=src_meta,
        )
        results["generation"] = await _safe("A_gen", "Generation", self.generation, gen_input, untouched)

        # ── Step 3: Quality (3-stage escalating retry) ───────────────────────
        quality_input = AgentInput(
            content=results["generation"].content, job_description=job_description,
            previous_output=results["generation"], metadata=src_meta,
        )
        results["quality"] = await _safe(
            "A_qual", "Quality", self.quality, quality_input,
            AgentOutput(content=results["generation"].content, quality_score=0.0, metadata={"degraded": True}),
        )

        # ── Step 4: Weak Detection ───────────────────────────────────────────
        weak_input = AgentInput(
            content=results["quality"].content, job_description=job_description, sections=sections,
            previous_output=results["quality"], metadata=src_meta,
        )
        results["weak_detection"] = await _safe(
            "A_weak", "Weak Detection", self.weak_detection, weak_input,
            AgentOutput(content=results["quality"].content, quality_score=0.0, metadata={"degraded": True}),
        )

        # ── Step 5: Tailoring (semantic alignment gate) ──────────────────────
        tailor_input = AgentInput(
            content=results["quality"].content, job_description=job_description, sections=sections,
            previous_output=results["weak_detection"], metadata=src_meta,
        )
        gate: dict[str, Any] | None = None
        try:
            results["tailoring"] = await _run_agent("A_tail", "Tailoring", self.tailoring, tailor_input)
        except AlignmentGateError as e:
            gate = {
                "alignment_score": round(e.alignment_score, 3),
                "threshold": settings.alignment_threshold,
                "weak_sections": e.weak_sections,
                "missing_skills": e.missing_skills,
            }
            await _emit(emit, {
                "event_type": "ALIGNMENT_GATE_ABORT",
                "agent_id": "A_tail",
                "timestamp": time.time(),
                "data": gate,
                "message": (
                    f"Tailoring skipped: alignment {e.alignment_score:.2f} is below "
                    f"{settings.alignment_threshold:.2f} — this role looks like a poor fit"
                ),
            })
            results["tailoring"] = AgentOutput(
                content=results["quality"].content,
                quality_score=e.alignment_score,
                metadata={"alignment_gate_aborted": True, "alignment_score": e.alignment_score, **gate},
            )
        except Exception as e:  # noqa: BLE001
            cause = (getattr(e, "context", None) or {}).get("last_error") or str(e)
            warnings.append({"stage": "Tailoring", "message": str(cause)[:300]})
            results["tailoring"] = AgentOutput(
                content=results["quality"].content, quality_score=0.0, metadata={"degraded": True}
            )

        # ── Steps 6+7: Interview + ATS in parallel ───────────────────────────
        final_for_downstream = results["tailoring"].content
        tasks: dict[str, Any] = {}
        if not skip_interview:
            tasks["interview"] = _run_agent(
                "A_int", "Interview", self.interview,
                AgentInput(content=final_for_downstream, job_description=job_description,
                           previous_output=results["tailoring"], metadata=src_meta),
            )
        tasks["ats"] = _run_agent(
            "A_ats", "ATS Simulation", self.ats,
            AgentInput(content=final_for_downstream, job_description=job_description, sections=sections,
                       previous_output=results["tailoring"], metadata=src_meta),
        )
        done = await asyncio.gather(*tasks.values(), return_exceptions=True)
        for name, out in zip(tasks, done):
            if isinstance(out, Exception):
                warnings.append({"stage": name, "message": str(out)[:300]})
                out = AgentOutput(content="", quality_score=0.0, metadata={"degraded": True})
            results[name] = out

        # ── Final metrics (all heuristic; see README "What the numbers mean") ─
        final_content = results["tailoring"].content
        impact_result = self.impact_scorer.score(final_content)
        keyword_result = self.keyword_scorer.score(final_content, job_description)
        ats_meta = results["ats"].metadata
        ats_score = int(ats_meta["aggregate_ats_score"] * 100) if "aggregate_ats_score" in ats_meta else None
        tailoring_meta = results["tailoring"].metadata
        alignment = tailoring_meta.get("alignment_score")
        grounding = check(final_content, [resume_text], job_description)
        if grounding.flagged:
            warnings.append({
                "stage": "Grounding",
                "message": "Final resume contains numbers or skills not present in your original: "
                           f"{(grounding.novel_numbers + grounding.injected_jd_terms)[:8]}",
            })

        metrics = {
            "alignment": round(float(alignment), 3) if alignment is not None else None,
            "alignmentThreshold": settings.alignment_threshold,
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
            "data": {"metrics": metrics, "warnings": warnings},
            "message": "Pipeline completed" + (f" with {len(warnings)} warning(s)" if warnings else ""),
        })

        logger.info("pipeline.complete", user_id=self.user_id, agents_run=list(results.keys()), warnings=len(warnings))

        return {
            "agents": {name: _serialize_output(output) for name, output in results.items()},
            "metrics": metrics,
            "warnings": warnings,
            "alignment_gate": gate,
            "grounding": grounding.as_dict(),
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
