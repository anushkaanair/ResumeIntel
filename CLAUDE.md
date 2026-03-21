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

## Reference Documents
- For agent specifications and pipeline details, see docs/agent-pipeline.md
- For RAG implementation details, see docs/rag-engine.md
- For API endpoint specs, see docs/api-design.md
- For architecture decisions, see docs/decisions/

## Team Division
- **AI + Backend (Neel)**: src/agents/, src/rag/, src/parsers/, src/scoring/, src/api/, src/config/
- **Frontend (Teammate)**: frontend/ — React dashboard, components, pages, hooks
