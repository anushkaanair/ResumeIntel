# Claude Code Project Blueprint
## AI-Powered Multi-Agent Resume & Career Intelligence System

---

## 1. PROJECT DIRECTORY STRUCTURE

```
resume-intel/
│
├── CLAUDE.md                          # Root project memory (< 150 lines)
├── README.md                          # Standard project readme
├── .mcp.json                          # MCP server config (if needed)
│
├── docs/
│   ├── architecture.md                # System architecture deep-dive
│   ├── agent-pipeline.md              # Agent specifications & pipeline flow
│   ├── rag-engine.md                  # RAG + FAISS implementation details
│   ├── api-design.md                  # Full API endpoint specs
│   └── decisions/
│       ├── 001-multi-agent-over-monolithic.md
│       ├── 002-faiss-over-pinecone.md
│       ├── 003-sbert-embedding-model.md
│       └── 004-fastapi-over-express.md
│
├── .claude/
│   ├── settings.json                  # Hooks, permissions, env
│   ├── settings.local.json            # Personal overrides (gitignored)
│   │
│   ├── skills/
│   │   ├── agent-builder/
│   │   │   └── SKILL.md              # How to create new agents
│   │   ├── api-endpoint/
│   │   │   └── SKILL.md              # FastAPI endpoint creation pattern
│   │   ├── rag-pipeline/
│   │   │   └── SKILL.md              # RAG retrieval + generation patterns
│   │   ├── react-component/
│   │   │   └── SKILL.md              # React component creation pattern
│   │   └── testing/
│   │       └── SKILL.md              # Testing patterns for this project
│   │
│   └── agents/
│       └── code-reviewer.md           # Subagent for code review
│
├── src/
│   ├── CLAUDE.md                      # Backend-specific context
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py              # Abstract BaseAgent class
│   │   ├── ingestion_agent.py
│   │   ├── generation_agent.py
│   │   ├── quality_agent.py
│   │   ├── weak_detection_agent.py
│   │   ├── tailoring_agent.py
│   │   └── interview_agent.py
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── embedder.py                # SBERT encoding
│   │   ├── vector_store.py            # FAISS operations
│   │   └── retriever.py               # Retrieval logic
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── resume_parser.py
│   │   └── jd_parser.py
│   ├── api/
│   │   ├── CLAUDE.md                  # API-specific context
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── resume.py
│   │   │   ├── optimize.py
│   │   │   └── export.py
│   │   └── schemas/
│   │       ├── resume.py              # Pydantic models
│   │       └── job.py
│   ├── scoring/
│   │   ├── __init__.py
│   │   ├── alignment.py
│   │   ├── keyword_coverage.py
│   │   └── impact_scorer.py
│   └── config/
│       ├── __init__.py
│       └── settings.py                # Pydantic Settings
│
├── frontend/
│   ├── CLAUDE.md                      # Frontend-specific context
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   └── lib/
│   ├── package.json
│   └── tsconfig.json
│
├── tests/
│   ├── agents/
│   ├── rag/
│   ├── api/
│   └── conftest.py
│
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── .env.example
```

---

## 2. CLAUDE.md (ROOT) — The Core Brain

This is the most critical file. Keep it under 150 lines, focused, and universally applicable.

```markdown
# Resume Intelligence System

## What This Is
Multi-agent AI system that optimizes resumes for ATS alignment using RAG-grounded generation.
6 specialized agents in a sequential pipeline. Python/FastAPI backend, React/TS frontend.

## Tech Stack
- Backend: Python 3.11, FastAPI 0.104, Celery 5.3 (Redis broker)
- Frontend: React 18, TypeScript 5, Tailwind CSS
- Vector DB: FAISS (IVF-PQ, 384-dim, all-MiniLM-L6-v2)
- Database: PostgreSQL 16
- Cache: Redis 7
- LLM: GPT-4o via OpenAI SDK (swappable)

## Key Architecture Decisions
- Multi-agent pipeline, NOT monolithic LLM — see docs/decisions/001-*.md
- RAG-grounded generation — every output traceable to source data
- Agents run sequentially: Ingestion → Generation → Quality → WeakDetection → Tailoring
- Interview agent runs in parallel on final output
- For agent design details, see docs/agent-pipeline.md

## Directory Map
- `src/agents/` — All 6 agents inherit from BaseAgent in base_agent.py
- `src/rag/` — SBERT embedder, FAISS store, retrieval logic
- `src/api/routes/` — FastAPI route handlers
- `src/api/schemas/` — Pydantic request/response models
- `src/parsers/` — Resume + JD parsing
- `src/scoring/` — Alignment, keyword coverage, impact scoring
- `frontend/` — React app (separate README)
- `tests/` — Mirrors src/ structure

## Commands
```bash
# Dev
uvicorn src.api:app --reload --port 8000
cd frontend && npm run dev

# Test
pytest tests/ -v
pytest tests/agents/test_quality_agent.py -v  # single agent

# Lint & Format
ruff check src/ --fix
ruff format src/

# Docker
docker compose up -d
docker compose logs -f backend
```

## Code Conventions
- Python: Ruff for linting+formatting, strict type hints everywhere
- All agents MUST inherit from BaseAgent and implement execute(), validate_input(), validate_output()
- Pydantic models for ALL API schemas — no raw dicts
- Async handlers in FastAPI routes
- Use structured logging (structlog), not print()
- Tests: pytest + pytest-asyncio, AAA pattern (Arrange, Act, Assert)
- Frontend: functional components, hooks only, no class components
- Tailwind for styling, no CSS modules

## Agent Quality Gates
Every agent must pass its quality gate before output propagates. If gate fails, retry up to 3x.
Do not skip quality gates. Do not bypass RAG grounding. No fabricated content ever.

## Important Constraints
- Never generate fake metrics or achievements — all content must trace to source
- Keep API responses under 200ms for sync endpoints
- FAISS indices are per-user isolated
- All PII must be detected and masked in logs
```

---

## 3. SUBDIRECTORY CLAUDE.md FILES

### src/CLAUDE.md
```markdown
# Backend Source

## Agent Implementation Pattern
Every agent follows this structure:
1. Inherit from `BaseAgent` (src/agents/base_agent.py)
2. Implement `execute(input: AgentInput) -> AgentOutput`
3. Implement `validate_input()` and `validate_output()`
4. Define quality gate criteria as class constants
5. Use structured logging for all operations

## Pipeline Order (DO NOT CHANGE)
Ingestion → Generation → Quality → WeakDetection → Tailoring → [Interview parallel]

## RAG Pattern
All generation agents MUST:
1. Call retriever.retrieve(query, top_k) FIRST
2. Include retrieved context in LLM prompt
3. Verify output against retrieved sources
4. Never generate from parametric memory alone

## Error Handling
- Use custom exception hierarchy from src/exceptions.py
- Agents catch and wrap errors in AgentError with context
- API routes return structured error responses via error middleware
```

### src/api/CLAUDE.md
```markdown
# API Layer

## Route Pattern
- All routes in src/api/routes/
- Pydantic models in src/api/schemas/
- Use dependency injection for services
- Async handlers, background tasks via Celery for optimization pipeline

## Response Format
All responses: {"status": "ok"|"error", "data": {...}, "meta": {...}}
Errors: {"status": "error", "error": {"code": "...", "message": "..."}}
```

### frontend/CLAUDE.md
```markdown
# Frontend

## Stack
React 18 + TypeScript 5 + Tailwind CSS + Framer Motion

## Structure
- components/ — Reusable UI (Button, Card, ScoreGauge, etc.)
- pages/ — Route-level components
- hooks/ — Custom hooks (useOptimize, useAlignment, etc.)
- lib/ — API client, utils, constants

## Conventions
- Functional components only, hooks for state
- Tailwind utility classes, no CSS modules
- All API calls through lib/api.ts
- Loading/error states for every async operation
- Framer Motion for transitions

## Component Pattern
Every component: named export, props interface, JSDoc description
```

---

## 4. SKILLS (`.claude/skills/`)

### Skill 1: agent-builder

```markdown
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

    QUALITY_THRESHOLD = 0.7  # Minimum score to pass gate
    MAX_RETRIES = 3

    def __init__(self, retriever: Retriever, llm_client):
        self.retriever = retriever
        self.llm = llm_client

    async def execute(self, input: AgentInput) -> AgentOutput:
        self.validate_input(input)

        # 1. Retrieve relevant context (RAG — mandatory)
        context = await self.retriever.retrieve(
            query=input.content,
            top_k=5
        )

        # 2. Build prompt with retrieved context
        prompt = self._build_prompt(input, context)

        # 3. Generate output
        result = await self.llm.generate(prompt)

        # 4. Validate output quality
        output = AgentOutput(content=result, sources=context)
        self.validate_output(output)

        logger.info("agent.complete", agent=self.__class__.__name__,
                     score=output.quality_score)
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
```

### Skill 2: api-endpoint

```markdown
---
name: api-endpoint
description: Create FastAPI endpoints for the resume intelligence API. Use when adding new routes, creating Pydantic schemas, or building API handlers. Triggers on "new endpoint", "add route", "API for", "create endpoint".
---

# API Endpoint Builder

## Route Pattern

```python
from fastapi import APIRouter, Depends, BackgroundTasks
from src.api.schemas.resume import OptimizeRequest, OptimizeResponse
from src.api.deps import get_pipeline_service

router = APIRouter(prefix="/api/v1", tags=["optimize"])

@router.post("/optimize", response_model=OptimizeResponse)
async def optimize_resume(
    request: OptimizeRequest,
    background_tasks: BackgroundTasks,
    service = Depends(get_pipeline_service),
):
    """Run full optimization pipeline on resume."""
    job_id = await service.start_optimization(request)
    return OptimizeResponse(
        status="ok",
        data={"job_id": job_id, "message": "Pipeline started"}
    )
```

## Schema Pattern

```python
from pydantic import BaseModel, Field

class OptimizeRequest(BaseModel):
    resume_text: str = Field(..., min_length=50, description="Resume content")
    job_description: str = Field(..., min_length=20, description="Target JD")
    options: OptimizeOptions | None = None

class OptimizeResponse(BaseModel):
    status: str
    data: dict
    meta: dict | None = None
```

## Rules
- Always use Pydantic models — no raw dicts
- Async handlers for all routes
- Heavy work → Celery background tasks
- Response format: {"status", "data", "meta"}
- Add route to src/api/__init__.py router includes
```

### Skill 3: rag-pipeline

```markdown
---
name: rag-pipeline
description: Implement RAG (Retrieval-Augmented Generation) patterns using SBERT embeddings and FAISS vector search. Use when working with embeddings, vector storage, retrieval logic, or grounding LLM outputs. Triggers on "embedding", "FAISS", "retrieval", "RAG", "vector search", "semantic search".
---

# RAG Pipeline Patterns

## Embedding
```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")  # 384-dim
embeddings = model.encode(segments, normalize_embeddings=True)
```

## FAISS Index
```python
import faiss
import numpy as np

dimension = 384
index = faiss.IndexIVFPQ(
    faiss.IndexFlatIP(dimension),  # Inner product (cosine after L2 norm)
    dimension, 100, 16, 8          # nlist=100, M=16, nbits=8
)
index.train(training_vectors)
index.add(vectors)
index.nprobe = 10  # Search 10 cells at query time
```

## Retrieval
```python
async def retrieve(self, query: str, top_k: int = 5) -> list[RetrievedSegment]:
    query_vector = self.embedder.encode([query], normalize_embeddings=True)
    scores, indices = self.index.search(query_vector, top_k)
    return [
        RetrievedSegment(
            content=self.segments[idx],
            score=float(score),
            segment_id=self.segment_ids[idx]
        )
        for score, idx in zip(scores[0], indices[0])
        if idx != -1
    ]
```

## Critical Rules
- ALWAYS normalize embeddings before FAISS inner product search
- ALWAYS use retrieval before generation — no parametric-only outputs
- Index type IVF-PQ for production, IndexFlatIP for testing (<10K vectors)
- Per-user index isolation — never mix user data
```

### Skill 4: react-component

```markdown
---
name: react-component
description: Create React components for the resume intelligence dashboard. Use when building UI components, pages, or interactive elements for the frontend. Triggers on "component", "dashboard", "UI for", "frontend widget", "React page".
---

# React Component Pattern

```tsx
import { useState } from "react";
import { motion } from "framer-motion";

interface AlignmentGaugeProps {
  /** Alignment score between 0 and 1 */
  score: number;
  /** Label shown below the gauge */
  label?: string;
}

/** Visual gauge showing resume-JD alignment score. */
export function AlignmentGauge({ score, label = "Alignment" }: AlignmentGaugeProps) {
  const percentage = Math.round(score * 100);
  const color = score >= 0.75 ? "text-green-500" : score >= 0.5 ? "text-yellow-500" : "text-red-500";

  return (
    <div className="flex flex-col items-center gap-2">
      <motion.div
        className={`text-4xl font-bold ${color}`}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
      >
        {percentage}%
      </motion.div>
      <span className="text-sm text-gray-500">{label}</span>
    </div>
  );
}
```

## Rules
- Named export, never default export
- Props interface with JSDoc on each prop
- JSDoc on the component itself
- Tailwind utility classes only
- Framer Motion for animations
- Loading + error states for async components
- API calls through lib/api.ts, not inline fetch
```

### Skill 5: testing

```markdown
---
name: testing
description: Write tests for the resume intelligence system using pytest and pytest-asyncio. Use when creating unit tests, integration tests, or test fixtures for agents, RAG, API, or scoring modules. Triggers on "write test", "add test", "test for", "testing", "pytest".
---

# Testing Patterns

## Agent Test
```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.agents.quality_agent import QualityAgent

@pytest.fixture
def mock_retriever():
    retriever = AsyncMock()
    retriever.retrieve.return_value = [
        RetrievedSegment(content="Built REST API with 99.9% uptime", score=0.89)
    ]
    return retriever

@pytest.fixture
def quality_agent(mock_retriever):
    return QualityAgent(retriever=mock_retriever, llm_client=AsyncMock())

@pytest.mark.asyncio
async def test_quality_agent_strengthens_weak_bullet(quality_agent):
    # Arrange
    input = AgentInput(content="Worked on API")

    # Act
    result = await quality_agent.execute(input)

    # Assert
    assert result.quality_score >= 0.7
    assert any(char.isdigit() for char in result.content)  # Has metrics
```

## API Test
```python
from httpx import AsyncClient, ASGITransport
from src.api import app

@pytest.mark.asyncio
async def test_optimize_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/optimize", json={
            "resume_text": "5 years Python experience...",
            "job_description": "Senior Backend Engineer..."
        })
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

## Rules
- AAA pattern: Arrange, Act, Assert
- Mock external dependencies (LLM, DB), never real calls in unit tests
- One assertion concept per test
- Fixtures in conftest.py for shared setup
- Test file mirrors source: src/agents/quality_agent.py → tests/agents/test_quality_agent.py
```

---

## 5. HOOKS (`.claude/settings.json`)

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "[ \"$(git branch --show-current)\" != \"main\" ] || { echo '{\"block\": true, \"message\": \"Cannot edit on main branch. Create a feature branch first.\"}' >&2; exit 2; }",
            "timeout": 5
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "echo \"$TOOL_INPUT\" | grep -qE 'rm\\s+-rf|git\\s+push\\s+--force|drop\\s+table|DROP\\s+DATABASE' && { echo '{\"block\": true, \"message\": \"Destructive command blocked.\"}' >&2; exit 2; } || exit 0",
            "timeout": 5
          }
        ]
      },
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "echo \"$TOOL_INPUT\" | grep -qiE '(api[_-]?key|secret|password|token)\\s*=\\s*[\"\\x27][^\"\\x27]+[\"\\x27]' && { echo '{\"block\": true, \"message\": \"Hardcoded secret detected. Use environment variables.\"}' >&2; exit 2; } || exit 0",
            "timeout": 5
          }
        ]
      }
    ]
  },
  "permissions": {
    "allow": [
      "Bash(ruff *)",
      "Bash(pytest *)",
      "Bash(uvicorn *)",
      "Bash(docker compose *)",
      "Bash(cd frontend && npm *)",
      "Bash(git status)",
      "Bash(git diff *)",
      "Bash(git add *)",
      "Bash(git commit *)",
      "Bash(git log *)",
      "Bash(git branch *)",
      "Bash(git checkout *)"
    ]
  }
}
```

### What the hooks do:
- **Branch protection**: Blocks edits when on `main` — forces feature branches
- **Destructive command guard**: Blocks `rm -rf`, `git push --force`, `DROP TABLE/DATABASE`
- **Secret detection**: Blocks writes that contain hardcoded API keys, passwords, tokens

### What the permissions do:
- Auto-approve common safe commands (linting, testing, git status/diff/commit)
- Reduces interruptions while keeping you in control for risky operations

---

## 6. DOCS (Architecture Decision Records)

### docs/decisions/001-multi-agent-over-monolithic.md
```markdown
# ADR-001: Multi-Agent Pipeline Over Monolithic LLM

## Status
Accepted

## Context
Resume optimization has competing objectives: alignment, keyword coverage,
impact quality, truthfulness, readability. A single LLM prompt cannot
optimize all simultaneously.

## Decision
Use 6 specialized agents in a sequential pipeline, each owning one objective.

## Consequences
- Better: Per-objective optimization, debuggable, independently tunable
- Worse: Higher latency (sequential), more infrastructure complexity
- Mitigated: Celery workers parallelize where possible, caching reduces repeated work
```

### docs/architecture.md
Point Claude here for the full system design. Include:
- Layer diagram (4 layers from the Godfather doc)
- Data flow from input to output
- Agent pipeline with interfaces
- RAG retrieval flow
- Database schema overview

### docs/agent-pipeline.md
Point Claude here for agent-specific details. Include:
- Each agent's input/output types
- Quality gate thresholds
- Retry behavior
- Pipeline composition equation

### docs/api-design.md
Full API spec. Include:
- All endpoints with request/response schemas
- Authentication flow
- Rate limiting strategy
- Error code reference

---

## 7. PROGRESSIVE DISCLOSURE STRATEGY

The key principle from the research: **don't tell Claude everything upfront — tell it where to find things.**

The root CLAUDE.md references docs like this:
```
## Reference Documents
- For agent specifications and pipeline details, see docs/agent-pipeline.md
- For RAG implementation details, see docs/rag-engine.md
- For API endpoint specs, see docs/api-design.md
- For architecture decisions, see docs/decisions/
```

Claude loads these only when the task requires it. This keeps context clean and focused.

Similarly, skills load automatically only when Claude detects a matching task — you don't pay context tokens for the `rag-pipeline` skill when you're building a React component.

---

## 8. RECOMMENDED BUILD ORDER

The order in which you should create these files when setting up:

**Phase 1 — Foundation (do this before any code)**
1. `CLAUDE.md` (root) — the core brain
2. `.claude/settings.json` — hooks + permissions
3. `docs/architecture.md` — system design reference
4. `docs/agent-pipeline.md` — agent specs
5. `docs/decisions/001-*.md` — key ADRs

**Phase 2 — Skills (do this before building each module)**
6. `.claude/skills/agent-builder/SKILL.md`
7. `.claude/skills/api-endpoint/SKILL.md`
8. `.claude/skills/rag-pipeline/SKILL.md`
9. `.claude/skills/testing/SKILL.md`
10. `.claude/skills/react-component/SKILL.md`

**Phase 3 — Subdirectory context (as you build)**
11. `src/CLAUDE.md`
12. `src/api/CLAUDE.md`
13. `frontend/CLAUDE.md`

**Phase 4 — Start coding (with Claude Code)**
14. `src/agents/base_agent.py` — foundation class
15. `src/rag/` — embedder, vector store, retriever
16. `src/agents/` — implement agents one by one
17. `src/api/` — routes + schemas
18. `frontend/` — dashboard components
19. Tests alongside each module

---

## 9. KEY PRINCIPLES TO REMEMBER

1. **CLAUDE.md < 150 lines**. Shorter is better. Claude can only attend to ~150-200 instructions reliably.

2. **Skills extend, hooks constrain.** Skills tell Claude what to do. Hooks tell Claude what it CAN'T do. Use hooks for safety rules (deterministic 100%), use CLAUDE.md for style preferences (probabilistic ~70%).

3. **Progressive disclosure.** Don't dump everything into CLAUDE.md. Reference docs by path, let Claude load them when needed.

4. **Document what Claude gets wrong.** After your first few sessions, add corrections to CLAUDE.md. "Don't use raw dicts for API responses" is better than "always use Pydantic" because it addresses the specific mistake.

5. **One skill per pattern.** Each skill = one well-defined workflow. Don't create a "backend" skill that tries to cover agents + API + RAG. Split them.

6. **Test your hooks immediately.** Try `rm -rf` and `git push --force` on a throwaway branch to confirm blocks work before doing real work.
