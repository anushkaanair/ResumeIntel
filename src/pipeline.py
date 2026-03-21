"""Pipeline Orchestrator — Runs the full agent pipeline sequentially."""

from __future__ import annotations

import asyncio

import structlog

from src.agents.base_agent import AgentInput, AgentOutput
from src.agents.generation_agent import GenerationAgent
from src.agents.ingestion_agent import IngestionAgent
from src.agents.interview_agent import InterviewAgent
from src.agents.quality_agent import QualityAgent
from src.agents.tailoring_agent import TailoringAgent
from src.agents.weak_detection_agent import WeakDetectionAgent
from src.rag.embedder import Embedder
from src.rag.retriever import Retriever
from src.rag.vector_store import VectorStore

logger = structlog.get_logger()


class Pipeline:
    """Orchestrates the sequential agent pipeline.

    Order: Ingestion → Generation → Quality → WeakDetection → Tailoring
    Interview agent runs in parallel on final output.
    """

    def __init__(self, llm_client: object, user_id: str = "default") -> None:
        self.llm = llm_client
        self.user_id = user_id

        # Shared RAG infrastructure
        self.embedder = Embedder()
        self.vector_store = VectorStore()
        self.retriever = Retriever(self.embedder, self.vector_store, user_id)

        # Initialize agents
        self.ingestion = IngestionAgent(self.retriever)
        self.generation = GenerationAgent(self.retriever, self.llm)
        self.quality = QualityAgent(self.retriever, self.llm)
        self.weak_detection = WeakDetectionAgent(self.retriever, self.llm)
        self.tailoring = TailoringAgent(self.retriever, self.llm)
        self.interview = InterviewAgent(self.retriever, self.llm)

    async def run(
        self,
        resume_text: str,
        job_description: str,
        skip_interview: bool = False,
    ) -> dict[str, AgentOutput]:
        """Run the full optimization pipeline.

        Returns:
            Dict with keys for each agent's output.
        """
        logger.info("pipeline.start", user_id=self.user_id)
        results: dict[str, AgentOutput] = {}

        # Step 1: Ingestion — parse and index
        input_data = AgentInput(content=resume_text, job_description=job_description)
        results["ingestion"] = await self.ingestion.run(input_data)

        # Step 2: Generation — create optimized bullets
        gen_input = AgentInput(
            content=resume_text,
            job_description=job_description,
            sections=results["ingestion"].sections,
            previous_output=results["ingestion"],
        )
        results["generation"] = await self.generation.run(gen_input)

        # Step 3: Quality — enforce standards
        quality_input = AgentInput(
            content=results["generation"].content,
            job_description=job_description,
            previous_output=results["generation"],
        )
        results["quality"] = await self.quality.run(quality_input)

        # Step 4: Weak Detection — find gaps
        weak_input = AgentInput(
            content=results["quality"].content,
            job_description=job_description,
            sections=results["ingestion"].sections,
            previous_output=results["quality"],
        )
        results["weak_detection"] = await self.weak_detection.run(weak_input)

        # Step 5: Tailoring — finalize for JD
        tailor_input = AgentInput(
            content=results["quality"].content,
            job_description=job_description,
            previous_output=results["weak_detection"],
        )
        results["tailoring"] = await self.tailoring.run(tailor_input)

        # Step 6: Interview (parallel, optional)
        if not skip_interview:
            interview_input = AgentInput(
                content=results["tailoring"].content,
                job_description=job_description,
                previous_output=results["tailoring"],
            )
            results["interview"] = await self.interview.run(interview_input)

        logger.info(
            "pipeline.complete",
            user_id=self.user_id,
            agents_run=list(results.keys()),
        )
        return results
