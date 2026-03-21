# ADR-001: Multi-Agent Pipeline Over Monolithic LLM Approach

**Date:** 2026-03-21

**Status:** Accepted

## Context

The system needs to perform multiple complex tasks on a resume: parsing, optimization, quality checking, weakness detection, tailoring to job descriptions, and interview preparation. The initial design consideration was between:

1. **Monolithic approach:** A single large LLM prompt that performs all tasks in one pass, receiving the resume and JD and producing the complete output.
2. **Multi-agent pipeline:** Six specialized agents, each handling one task, passing structured outputs sequentially.

The monolithic approach is simpler to implement but produces unreliable results for complex multi-step reasoning. In early prototyping, a single prompt approach frequently produced inconsistent quality scores, skipped weakness detection, and generated shallow interview prep. The output was difficult to validate incrementally, and a failure in any part required re-running the entire generation.

## Decision

We will use a sequential multi-agent pipeline with six specialized agents: IngestionAgent, GenerationAgent, QualityAgent, WeakDetectionAgent, TailoringAgent, and InterviewAgent. Each agent has a single responsibility, well-defined input/output types, its own validation logic, and independent retry capability.

## Consequences

### Better

- **Single responsibility:** Each agent focuses on one task, producing higher-quality results than a single prompt attempting everything.
- **Incremental validation:** Quality gates between agents catch problems early. A bad generation is retried before it reaches tailoring.
- **Debuggability:** When output quality drops, the failing agent is immediately identifiable through per-agent scoring and logs.
- **Independent improvement:** Each agent's prompt, model, or logic can be upgraded without touching the others. The QualityAgent can be made stricter without rewriting the GenerationAgent.
- **Progress tracking:** The frontend can show step-by-step progress (e.g., "Step 3/6: Quality check") because each agent is a discrete step.
- **Retry isolation:** A failure in interview prep generation does not require re-running resume parsing and optimization.
- **Testability:** Each agent can be unit tested with fixed inputs and expected outputs.

### Worse

- **Higher latency:** Sequential execution of six agents is slower than a single LLM call. Estimated total pipeline time is 30-60 seconds compared to 10-20 seconds for a monolithic approach.
- **More code complexity:** Six agent classes, six input/output type definitions, pipeline orchestration logic, and inter-agent data contracts add significant codebase complexity.
- **Higher token usage:** Each agent call consumes tokens independently. Some context is duplicated across agents (e.g., the JD is passed to multiple agents).
- **Inter-agent coupling:** Changes to one agent's output schema can break downstream agents, requiring coordinated updates.

### Mitigated

- **Latency** is mitigated by running the pipeline as an async background task with status polling, so the user is not blocked.
- **Code complexity** is mitigated by a shared `BaseAgent` interface and a `Pipeline` orchestrator that handles execution, retries, and progress reporting.
- **Token usage** is mitigated by keeping individual agent prompts focused and using RAG to provide only relevant context rather than the full resume at every stage.
- **Inter-agent coupling** is mitigated by defining explicit Pydantic models for all inter-agent contracts, with schema validation at each boundary.
