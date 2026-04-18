"""Pipeline Orchestrator — Runs the full agent pipeline sequentially.

Event emission:
  Pass an async `event_callback(event: dict) -> None` to run() and it will be
  called after every agent completes with a typed AgentEvent payload.
  optimize.py uses this to push events into the per-job asyncio.Queue consumed
  by the WebSocket handler in ws.py.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

import structlog

from src.agents.ats_agent import ATSAgent
from src.agents.base_agent import AgentInput, AgentOutput
from src.agents.generation_agent import GenerationAgent
from src.agents.ingestion_agent import IngestionAgent
from src.agents.interview_agent import InterviewAgent
from src.agents.quality_agent import QualityAgent
from src.agents.tailoring_agent import TailoringAgent
from src.agents.weak_detection_agent import WeakDetectionAgent
from src.config.industry_profiles import IndustryProfile
from src.rag.embedder import Embedder
from src.rag.retriever import Retriever
from src.rag.vector_store import VectorStore

logger = structlog.get_logger()

EventCallback = Callable[[dict[str, Any]], Awaitable[None]]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Pipeline:
    """Orchestrates the sequential agent pipeline.

    Order: Ingestion → Generation → Quality → WeakDetection → [Tailoring ∥ Interview]
    Tailoring and Interview run concurrently via asyncio.gather after WeakDetection.
    """

    def __init__(
        self,
        llm_client: object,
        user_id: str = "default",
        industry_profile: IndustryProfile | None = None,
        resume_text_for_lang_detect: str = "",
    ) -> None:
        self.llm = llm_client
        self.user_id = user_id

        # Shared RAG infrastructure — auto-detect language for non-English resumes
        self.embedder = Embedder(
            auto_detect=bool(resume_text_for_lang_detect),
            sample_text=resume_text_for_lang_detect,
        )
        self.vector_store = VectorStore()
        self.retriever = Retriever(self.embedder, self.vector_store, user_id)

        # Initialize agents
        self.ingestion = IngestionAgent(self.retriever)
        self.generation = GenerationAgent(self.retriever, self.llm)
        self.quality = QualityAgent(self.retriever, self.llm)
        self.weak_detection = WeakDetectionAgent(self.retriever, self.llm)
        self.tailoring = TailoringAgent(self.retriever, self.llm, industry_profile)
        self.interview = InterviewAgent(self.retriever, self.llm)
        self.ats = ATSAgent()

    async def run(
        self,
        resume_text: str,
        job_description: str,
        skip_interview: bool = False,
        event_callback: EventCallback | None = None,
    ) -> dict[str, AgentOutput]:
        """Run the full optimization pipeline.

        Args:
            resume_text:     Raw resume text.
            job_description: Target JD text.
            skip_interview:  Skip interview prep agent.
            event_callback:  Async callable invoked after each agent with a typed
                             AgentEvent dict. Used by optimize.py to push WS events.

        Returns:
            Dict mapping agent name → AgentOutput.
        """
        logger.info("pipeline.start", user_id=self.user_id)
        results: dict[str, AgentOutput] = {}

        async def _emit(agent_name: str, output: AgentOutput) -> None:
            if event_callback is None:
                return
            gate_passed = output.status not in ("alignment_gate_failed", "quality_gate_failed")
            await event_callback({
                "event_type": "agent_complete",
                "agent_name": agent_name,
                "timestamp": _now(),
                "quality_gate_passed": gate_passed,
                "quality_score": round(output.quality_score, 4),
                "partial_result": {
                    "unresolvable_count": output.metadata.get("unresolvable_count", 0),
                    "status": output.status,
                    **(
                        {
                            "weakest_sections": output.metadata.get("weakest_sections", []),
                            "alignment_score": output.metadata.get("alignment_score"),
                        }
                        if output.status == "alignment_gate_failed"
                        else {}
                    ),
                },
                "message": (
                    output.metadata.get("message", f"{agent_name} completed")
                    if output.status != "ok"
                    else f"{agent_name} agent completed successfully"
                ),
            })

        # ------------------------------------------------------------------
        # Step 1: Ingestion
        # ------------------------------------------------------------------
        await _emit_start(event_callback, "ingestion")
        input_data = AgentInput(content=resume_text, job_description=job_description)
        results["ingestion"] = await self.ingestion.run(input_data)
        await _emit("ingestion", results["ingestion"])

        # ------------------------------------------------------------------
        # Step 2: Generation
        # ------------------------------------------------------------------
        await _emit_start(event_callback, "generation")
        gen_input = AgentInput(
            content=resume_text,
            job_description=job_description,
            sections=results["ingestion"].sections,
            previous_output=results["ingestion"],
        )
        results["generation"] = await self.generation.run(gen_input)
        await _emit("generation", results["generation"])

        # ------------------------------------------------------------------
        # Step 3: Quality
        # ------------------------------------------------------------------
        await _emit_start(event_callback, "quality")
        quality_input = AgentInput(
            content=results["generation"].content,
            job_description=job_description,
            previous_output=results["generation"],
        )
        results["quality"] = await self.quality.run(quality_input)
        await _emit("quality", results["quality"])

        # ------------------------------------------------------------------
        # Step 4: Weak Detection
        # ------------------------------------------------------------------
        await _emit_start(event_callback, "weak_detection")
        weak_input = AgentInput(
            content=results["quality"].content,
            job_description=job_description,
            sections=results["ingestion"].sections,
            previous_output=results["quality"],
        )
        results["weak_detection"] = await self.weak_detection.run(weak_input)
        await _emit("weak_detection", results["weak_detection"])

        # ------------------------------------------------------------------
        # Step 5+6: Tailoring ∥ Interview (parallel)
        # ------------------------------------------------------------------
        tailor_input = AgentInput(
            content=results["quality"].content,
            job_description=job_description,
            sections=results["ingestion"].sections,
            previous_output=results["weak_detection"],
        )
        interview_input = AgentInput(
            content=results["quality"].content,
            job_description=job_description,
            previous_output=results["weak_detection"],
        )

        await _emit_start(event_callback, "tailoring")
        if skip_interview:
            results["tailoring"] = await self.tailoring.run(tailor_input)
            await _emit("tailoring", results["tailoring"])
        else:
            await _emit_start(event_callback, "interview")
            tailoring_out, interview_out = await asyncio.gather(
                self.tailoring.run(tailor_input),
                self.interview.run(interview_input),
            )
            results["tailoring"] = tailoring_out
            results["interview"] = interview_out
            await _emit("tailoring", tailoring_out)
            await _emit("interview", interview_out)

        # ------------------------------------------------------------------
        # Step 7: ATS Simulation (after tailoring, advisory only)
        # ------------------------------------------------------------------
        await _emit_start(event_callback, "ats")
        from src.parsers.jd_parser import JDParser
        _jd_parser = JDParser()
        parsed_jd = _jd_parser.parse(job_description)
        ats_input = AgentInput(
            content=results["tailoring"].content,
            job_description=job_description,
            metadata={"jd_keywords": parsed_jd.keywords},
        )
        results["ats"] = await self.ats.run(ats_input)
        await _emit("ats", results["ats"])

        # ------------------------------------------------------------------
        # Pipeline complete sentinel
        # ------------------------------------------------------------------
        if event_callback is not None:
            final = results.get("tailoring")
            await event_callback({
                "event_type": "pipeline_complete",
                "agent_name": "",
                "timestamp": _now(),
                "quality_gate_passed": True,
                "quality_score": round(final.quality_score, 4) if final else None,
                "partial_result": {"agents_run": list(results.keys())},
                "message": "Pipeline completed successfully",
            })

        logger.info(
            "pipeline.complete",
            user_id=self.user_id,
            agents_run=list(results.keys()),
        )
        return results


async def _emit_start(callback: EventCallback | None, agent_name: str) -> None:
    if callback is None:
        return
    await callback({
        "event_type": "agent_start",
        "agent_name": agent_name,
        "timestamp": _now(),
        "quality_gate_passed": None,
        "quality_score": None,
        "partial_result": {},
        "message": f"{agent_name} agent started",
    })
