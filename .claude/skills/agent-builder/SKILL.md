---
name: agent-builder
description: Create new agents for the resume optimization pipeline. Use when adding a new agent, modifying agent behavior, or extending the pipeline with new capabilities. Triggers on mentions of "new agent", "add agent", "agent for", "extend pipeline".
---

# Agent Builder

## When to Use
- Creating a new agent for the pipeline
- Modifying an existing agent's behavior
- Adding a new quality gate

## Agent Template

Every agent MUST follow this structure:

```python
from src.agents.base_agent import BaseAgent, AgentInput, AgentOutput
from src.rag.retriever import Retriever
import structlog

logger = structlog.get_logger()

class NewAgent(BaseAgent):
    """One-line description of what this agent does."""

    QUALITY_THRESHOLD = 0.7
    MAX_RETRIES = 3

    def __init__(self, retriever: Retriever, llm_client):
        self.retriever = retriever
        self.llm = llm_client

    async def execute(self, input: AgentInput) -> AgentOutput:
        self.validate_input(input)

        # 1. Retrieve relevant context (RAG — mandatory)
        context = await self.retriever.retrieve(query=input.content, top_k=5)

        # 2. Build prompt with retrieved context
        prompt = self._build_prompt(input, context)

        # 3. Generate output
        result = await self.llm.generate(prompt)

        # 4. Validate output quality
        output = AgentOutput(content=result, sources=context)
        self.validate_output(output)

        logger.info("agent.complete", agent=self.__class__.__name__, score=output.quality_score)
        return output

    def validate_input(self, input: AgentInput) -> None:
        if not input.content:
            raise ValueError("Empty input content")

    def validate_output(self, output: AgentOutput) -> None:
        if output.quality_score < self.QUALITY_THRESHOLD:
            raise QualityGateError(f"Score {output.quality_score} below threshold")
```

## Checklist
- [ ] Inherits from BaseAgent
- [ ] Has RAG retrieval step
- [ ] Quality gate defined with threshold
- [ ] Structured logging
- [ ] Input/output validation
- [ ] Retry logic (via BaseAgent)
- [ ] Unit tests in tests/agents/
