# ResumeIntel — Project Status

> Last updated: 2026-04-23
> Branch: `feature/p0-pipeline-fixes`
> Repo: [github.com/anushkaanair/ResumeIntel](https://github.com/anushkaanair/ResumeIntel)

---

## Summary

| Layer | Status |
|---|---|
| Multi-Agent Pipeline | Complete |
| RAG System | Complete |
| Core API | Complete |
| Database Schema | Complete |
| Alembic Migrations | Setup complete, first migration pending |
| Frontend Pages | 4/5 complete |
| Frontend Components | Complete |
| WebSocket Streaming | Complete |
| Profile Sync (GitHub/LinkedIn) | Backend complete, frontend wired |
| Collaborative Review | Backend complete, frontend component scaffolded |
| Version History | Backend complete, frontend component scaffolded |
| ATS Simulation | Complete |
| Export (PDF/DOCX) | Backend complete |
| E2E Integration Tests | Not started |
| Unit / Agent Tests | Scaffolded, partial coverage |
| Production Deployment | Not started |

---

## What Is Done

### Backend

#### Multi-Agent Pipeline
All 7 agents are implemented, tested individually, and wired into the pipeline orchestrator.

- **Ingestion Agent** — Parses resume into sections, indexes segments into FAISS. Quality gate at 0.7.
- **Generation Agent** — RAG-grounded bullet generation with strict no-fabrication rules. Quality gate at 0.7.
- **Quality Agent** — Two-stage bullet QA with per-bullet retry and escalating prompts (3 escalation levels). Flags unresolvable bullets.
- **Weak Detection Agent** — Keyword gap analysis, section completeness, vague bullet detection, low-similarity RAG check.
- **Tailoring Agent** — Alignment gate (cosine similarity ≥ 0.6 required), industry profile classification (6 profiles), JD-keyword integration, section reordering.
- **Interview Agent** — STAR-framework behavioral questions, technical questions, talking points, questions to ask interviewer.
- **ATS Agent** — Simulates Workday, Greenhouse, Lever, Taleo. Weighted ATS score. Advisory only (quality gate = 0.0).
- **Sync Agent** — GitHub repo and LinkedIn position/skill delta fetch with cursor-based pagination, JD relevance scoring, auto-section classification.

**Pipeline orchestrator** (`src/pipeline.py`):
- Sequential execution with parallel branch (Tailoring ∥ Interview)
- Shared RAG infrastructure across all agents
- Per-user FAISS index isolation
- Event callback for WebSocket streaming
- Retry logic with quality gates
- Full status lifecycle: `queued → running → completed → failed`

---

#### RAG System
- SBERT embedder with automatic English/multilingual model switching (`langdetect`)
- FAISS `IndexFlatIP` per user, persisted to disk
- Retriever with `index_segments`, `retrieve`, `retrieve_by_section`, `get_stats`
- Alignment scorer: full similarity matrix, section-level scores, gap detection

---

#### API Layer
All route files implemented under `src/api/routes/`:

| Route File | Endpoints |
|---|---|
| `resume.py` | Upload + text extraction |
| `optimize.py` | Start pipeline, status poll, result fetch, alignment score |
| `canvas.py` | Canvas state, bullet score/suggest/accept, section reoptimize/enhance, profile refresh, export, dispute |
| `interview.py` | Fetch prep data, generate, practice answer |
| `jd.py` | Parse JD, fetch by ID |
| `export.py` | PDF and DOCX export |
| `sync.py` | Connect OAuth, status, refresh, list deltas, apply delta |
| `collab.py` | Create session, get session, get/add annotations |
| `versions.py` | Snapshot, list, diff, revert |
| `ws.py` | WebSocket event stream |

---

#### Database
Full schema defined in `src/db/models.py`:
- `users`, `resumes`, `optimization_runs`
- `profile_sync_states`, `sync_deltas`
- `collab_sessions`, `mentor_annotations`

Alembic configured (`alembic.ini`, `alembic/env.py`). Migration history directory exists. **First migration has not been generated yet** (models exist but `alembic revision --autogenerate` has not been run against a live database).

---

#### Config
- `pydantic-settings` environment loader (`settings.py`)
- 6 industry profiles with per-profile scoring weights, tone, format rules (`industry_profiles.py`)

---

#### Parsers & Scoring
- Resume parser: PDF (PyPDF2), DOCX (python-docx), TXT
- JD parser: Regex-based title, requirements, responsibilities, qualifications, skills, keywords
- Impact scorer: Per-bullet strong verb / metric / length / technical term scoring
- Alignment scorer: SBERT similarity matrix, section-level scores, gap list

---

#### Infrastructure
- `docker-compose.yml` — Production: backend + postgres:16 + redis:7
- `docker-compose.dev.yml` — Dev override with live-mount volumes
- `.env.example` — All required keys documented

---

### Frontend

#### Pages

| Page | Route | Status |
|---|---|---|
| HomePage | `/` | Complete — animated hero, scroll reveal, feature cards |
| OptimizePage | `/optimize` | Complete — drag-drop upload, PDF extraction, all input fields |
| CanvasPage | `/canvas/:id` | Complete — 3-panel editor, bullet edit/suggest/accept, version timeline, profile sync, export |
| InterviewPage | `/interview/:id` | Complete — gap analysis, question categories, STAR prep, practice mode with AI feedback |
| ResultsPage | `/results/:id` | Stub — basic component exists, full implementation pending |

---

#### Components
All components implemented under `frontend/src/components/`:

- **Layout/Nav:** `Navbar`, `Footer`, `Card`
- **Metrics:** `AlignmentGauge`, `ScoreBadge`, `KeywordChips`, `WeaknessCard`
- **Upload:** `PdfUploadZone`
- **Canvas-specific:** `ResumePreview`, `SuggestionList`, `WhyButton`, `VersionTimeline`, `StalenessIndicator`
- **Collaboration:** `MentorAnnotationPanel`
- **Profile Sync:** `ProfileSyncPanel`
- **Utility:** `Button`, `LoadingSpinner`

---

#### State Management
- **canvasStore** (Zustand + persist): Full canvas state, per-bullet undo stacks, bullet provenance, pipeline agent states
- **interviewStore** (Zustand): Interview page state
- **themeStore** (Zustand): Dark/light mode

---

## What Is Left To Do

### High Priority

#### 1. Run First Alembic Migration
The database models are defined but no migration has been generated against a real database.

```bash
# With a running postgres container:
docker compose up -d postgres
docker compose exec backend alembic revision --autogenerate -m "initial schema"
docker compose exec backend alembic upgrade head
```

**Blocks:** Any persistent storage. Without this, the backend only works in-memory.

---

#### 2. Complete ResultsPage
**File:** [frontend/src/pages/ResultsPage.tsx](frontend/src/pages/ResultsPage.tsx)

Currently a stub. Needs:
- Overall alignment score visualization
- Per-agent output cards (quality, tailoring, ATS)
- Keyword coverage breakdown
- "Proceed to Canvas" and "View Interview Prep" CTAs
- Connect to `GET /optimize/{job_id}/result`

---

#### 3. E2E Integration: WebSocket ↔ Pipeline ↔ Frontend
**Files:** [frontend/src/pages/CanvasPage.tsx](frontend/src/pages/CanvasPage.tsx), [src/api/routes/ws.py](src/api/routes/ws.py)

The WebSocket handler and pipeline event emitter are both implemented, but the frontend WebSocket client in CanvasPage needs full validation:

- Connect on page load using `job_id` from URL
- Handle all event types: `agent_start`, `agent_complete`, `pipeline_complete`, `error`
- Update `canvasStore.pipeline` state in real-time
- Show agent progress indicators in the UI
- Handle reconnection and timeout gracefully

---

#### 4. `.env` Configuration for Deployment
**File:** [.env.example](.env.example)

Required before any deployed instance works:
- `OPENAI_API_KEY` — LLM calls
- `DATABASE_URL` — PostgreSQL connection
- `REDIS_URL` — Celery + WebSocket queues
- `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` — Profile sync OAuth
- `LINKEDIN_CLIENT_ID` / `LINKEDIN_CLIENT_SECRET` — Profile sync OAuth

---

### Medium Priority

#### 5. Integration Test Suite
**Directory:** [tests/](tests/)

Test scaffolding exists (`tests/agents/`, `tests/api/`, `tests/rag/`) but coverage is partial.

Remaining tests needed:
- `test_pipeline.py` — Full pipeline run with mock LLM responses
- `test_ws.py` — WebSocket event ordering and reconnect
- `test_sync_agent.py` — Delta fetch with mocked GitHub/LinkedIn APIs
- `test_ats_agent.py` — Per-platform checks
- `test_collab.py` — Session creation and annotation CRUD
- `test_versions.py` — Snapshot, diff, revert flow

---

#### 6. Auth System
Currently no user authentication. The system uses `user_id` strings passed in requests, with no verification.

Needed:
- JWT-based auth (or OAuth via GitHub/LinkedIn SSO)
- Middleware to inject `user_id` from token
- Protect all per-user routes (`/canvas`, `/sync`, `/collab`, `/versions`)

---

#### 7. Celery Integration
`celery_job_id` is stored in `OptimizationRun` but the pipeline currently runs via `asyncio.BackgroundTasks`, not a Celery worker.

Needed:
- `celery_app.py` with Redis broker
- Pipeline task registered as `@celery_app.task`
- Celery worker startup (`celery -A src.celery_app worker`)
- Update `POST /optimize` to submit Celery task and store task ID

---

#### 8. OAuth Flow for Profile Sync
The sync routes accept a raw `access_token` from the client. A proper OAuth flow is needed:

- GitHub OAuth: `/auth/github` → GitHub → `/auth/github/callback`
- LinkedIn OAuth: `/auth/linkedin` → LinkedIn → `/auth/linkedin/callback`
- Store encrypted tokens in `profile_sync_states`

---

### Low Priority

#### 9. Production Deployment Setup
**Backend:** Render or AWS ECS
**Frontend:** Vercel or Netlify
**Database:** Managed PostgreSQL (Render, Supabase, or RDS)
**Redis:** Managed Redis (Upstash or ElastiCache)

Needed:
- `Dockerfile` production hardening (non-root user, no dev deps)
- Environment variable injection via platform secrets
- CORS origins set to production domain
- Frontend `VITE_API_URL` set to deployed backend URL

---

#### 10. Collaborative Review — Full UX
`collab.py` and `MentorAnnotationPanel` are implemented, but the sharing flow needs:
- Shareable link generation and copy-to-clipboard on CanvasPage
- Read-only mode for shared sessions (viewer role)
- Real-time annotation sync (WebSocket or polling)

---

#### 11. Version Diff UI
`VersionTimeline` component exists, but the visual diff view (additions / removals highlighted inline) is not wired to `GET /versions/{job_id}/diff`. Needs a diff rendering component.

---

#### 12. FAISS IVF-PQ for Scale
The current FAISS index type is `IndexFlatIP` (exact search). For production scale (many users, large corpora), this should migrate to `IndexIVFPQ` with nlist/nprobe tuning.

---

## Known Issues

| Issue | Impact | Notes |
|---|---|---|
| No database migrations generated | Blocks persistent storage | Run `alembic revision --autogenerate` against live DB |
| No auth middleware | Security gap | All routes are open; `user_id` is client-supplied |
| Pipeline runs in `BackgroundTasks`, not Celery | Scalability | Works for demo; breaks under load |
| ResultsPage is a stub | UX gap | Users land on an empty page post-optimization |
| LinkedIn API v2 requires approved app | Profile sync blocked | Must register app with LinkedIn Developer Portal |
| OAuth tokens stored as plaintext in dev | Security | Fernet encryption is in models but key must be set in `.env` |

---

## File Structure Reference

```
AI_Resume_System/
├── src/
│   ├── agents/
│   │   ├── base_agent.py          ✅ Complete
│   │   ├── ingestion_agent.py     ✅ Complete
│   │   ├── generation_agent.py    ✅ Complete
│   │   ├── quality_agent.py       ✅ Complete
│   │   ├── weak_detection_agent.py ✅ Complete
│   │   ├── tailoring_agent.py     ✅ Complete
│   │   ├── interview_agent.py     ✅ Complete
│   │   ├── ats_agent.py           ✅ Complete
│   │   └── sync_agent.py          ✅ Complete
│   ├── api/
│   │   ├── __init__.py            ✅ Complete
│   │   └── routes/
│   │       ├── resume.py          ✅ Complete
│   │       ├── optimize.py        ✅ Complete
│   │       ├── canvas.py          ✅ Complete
│   │       ├── interview.py       ✅ Complete
│   │       ├── jd.py              ✅ Complete
│   │       ├── export.py          ✅ Complete
│   │       ├── sync.py            ✅ Complete
│   │       ├── collab.py          ✅ Complete
│   │       ├── versions.py        ✅ Complete
│   │       └── ws.py              ✅ Complete
│   ├── rag/
│   │   ├── embedder.py            ✅ Complete
│   │   ├── vector_store.py        ✅ Complete
│   │   └── retriever.py           ✅ Complete
│   ├── parsers/
│   │   ├── resume_parser.py       ✅ Complete
│   │   └── jd_parser.py           ✅ Complete
│   ├── scoring/
│   │   ├── alignment.py           ✅ Complete
│   │   └── impact_scorer.py       ✅ Complete
│   ├── config/
│   │   ├── settings.py            ✅ Complete
│   │   └── industry_profiles.py   ✅ Complete
│   ├── db/
│   │   └── models.py              ✅ Complete
│   └── pipeline.py                ✅ Complete
├── frontend/src/
│   ├── pages/
│   │   ├── HomePage.tsx           ✅ Complete
│   │   ├── OptimizePage.tsx       ✅ Complete
│   │   ├── CanvasPage.tsx         ✅ Complete
│   │   ├── InterviewPage.tsx      ✅ Complete
│   │   └── ResultsPage.tsx        🔲 Stub — needs implementation
│   ├── components/
│   │   ├── AlignmentGauge.tsx     ✅ Complete
│   │   ├── Button.tsx             ✅ Complete
│   │   ├── Card.tsx               ✅ Complete
│   │   ├── Footer.tsx             ✅ Complete
│   │   ├── KeywordChips.tsx       ✅ Complete
│   │   ├── LoadingSpinner.tsx     ✅ Complete
│   │   ├── MentorAnnotationPanel.tsx ✅ Complete
│   │   ├── Navbar.tsx             ✅ Complete
│   │   ├── PdfUploadZone.tsx      ✅ Complete
│   │   ├── ProfileSyncPanel.tsx   ✅ Complete
│   │   ├── ResumePreview.tsx      ✅ Complete
│   │   ├── ScoreBadge.tsx         ✅ Complete
│   │   ├── StalenessIndicator.tsx ✅ Complete
│   │   ├── SuggestionList.tsx     ✅ Complete
│   │   ├── VersionTimeline.tsx    ✅ Complete
│   │   ├── WeaknessCard.tsx       ✅ Complete
│   │   └── WhyButton.tsx          ✅ Complete
│   └── stores/
│       ├── canvasStore.ts         ✅ Complete
│       ├── interviewStore.ts      ✅ Complete
│       └── themeStore.ts          ✅ Complete
├── alembic/                       ✅ Setup complete — first migration pending
├── tests/                         🔲 Scaffolded — partial coverage
├── docker-compose.yml             ✅ Complete
├── docker-compose.dev.yml         ✅ Complete
├── .env.example                   ✅ Complete
└── pyproject.toml                 ✅ Complete
```

---

## Next Immediate Steps (in priority order)

1. Run the first Alembic migration against a live PostgreSQL instance
2. Implement `ResultsPage.tsx` to complete the optimization flow
3. Validate WebSocket ↔ pipeline ↔ CanvasPage event handling end-to-end
4. Fill in `.env` with real keys for a local full-stack run
5. Write the remaining integration tests (pipeline, WebSocket, sync, collab, versions)
6. Add JWT auth middleware
7. Wire Celery properly for background task execution
8. Set up production deployment (backend + frontend + managed DB)
