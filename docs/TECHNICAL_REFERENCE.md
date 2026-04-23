# ResumeIntel — Technical Reference

> Complete specification for the multi-agent AI resume optimization system.
> Stack: Python 3.11 · FastAPI · React 18 · FAISS · PostgreSQL 16 · Redis 7

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [API Endpoints](#api-endpoints)
3. [Agent Pipeline](#agent-pipeline)
4. [RAG System](#rag-system)
5. [Database Schema](#database-schema)
6. [Parsers & Scoring](#parsers--scoring)
7. [Config & Industry Profiles](#config--industry-profiles)
8. [Frontend — Pages](#frontend--pages)
9. [Frontend — Components](#frontend--components)
10. [Frontend — State Management](#frontend--state-management)
11. [Infrastructure](#infrastructure)
12. [Dependencies](#dependencies)

---

## Architecture Overview

```
User
 │
 ▼
React Frontend (Vite + TypeScript)
 │  REST + WebSocket
 ▼
FastAPI Backend (port 8000)
 │
 ├── Multi-Agent Pipeline ──────────────────────────────────────────
 │    Ingestion → Generation → Quality → WeakDetection
 │                                          ├── Tailoring (parallel)
 │                                          └── Interview (parallel)
 │                                                   └── ATS
 │
 ├── RAG Layer
 │    SBERT Embedder (all-MiniLM-L6-v2, 384-dim)
 │    FAISS Vector Store (per-user isolated indices)
 │    Retriever (semantic search, top-k)
 │
 ├── Database Layer
 │    PostgreSQL 16 (users, resumes, runs, sync, collab, versions)
 │    Alembic (schema migrations)
 │
 └── Cache / Broker
      Redis 7 (job queues, Celery tasks, WebSocket event queues)
```

**Design principles:**
- Every agent inherits `BaseAgent` and must pass a quality gate before output propagates
- All generated content is RAG-grounded — no fabricated metrics
- Per-user FAISS indices enforce data isolation
- Real-time pipeline status via WebSocket event streaming

---

## API Endpoints

Base URL: `http://localhost:8000/api/v1`

---

### Resume

#### `POST /resume/upload`
Upload a resume file. Extracts raw text for downstream processing.

| Field | Type | Notes |
|---|---|---|
| `file` | File (multipart) | PDF, DOCX, DOC, TXT |

**Response**
```json
{
  "filename": "resume.pdf",
  "raw_text": "...",
  "char_count": 3241
}
```

---

### Optimize

#### `POST /optimize`
Kick off the full agent pipeline for a resume + job description.

**Request**
```json
{
  "resume_text": "...",
  "job_description": "...",
  "options": {
    "skip_interview": false,
    "user_id": "uuid"
  }
}
```

**Response**
```json
{ "job_id": "uuid" }
```

Pipeline runs in background. Connect to `/ws/optimize/{job_id}` for live events.

---

#### `GET /optimize/{job_id}/status`
Poll pipeline progress.

**Response**
```json
{
  "status": "ok",
  "data": {
    "job_id": "uuid",
    "job_status": "running | completed | error"
  }
}
```

---

#### `GET /optimize/{job_id}/result`
Fetch full pipeline output once completed.

**Response** — Per-agent output including `content`, `quality_score`, `status`, `suggestions`, `metadata`, and `provenance`.

---

#### `POST /alignment/score`
Score resume-JD semantic alignment without running the full pipeline.

**Request**
```json
{
  "resume_text": "...",
  "job_description": "..."
}
```

**Response**
```json
{
  "overall_score": 0.74,
  "gaps": ["cloud infrastructure", "CI/CD"],
  "section_scores": { "experience": 0.81, "skills": 0.67 }
}
```

---

### Canvas

The canvas is the interactive resume editor powered by per-bullet scoring and AI suggestion.

#### `GET /canvas/{resume_id}/state`
Full canvas state for a given resume.

**Response** — Resume object, metrics, parsed JD, pipeline agent states.

---

#### `POST /canvas/bullet/{bullet_id}/score`
Score a single bullet for impact and alignment.

**Request** `{ "text": "Led migration of monolith to microservices, reducing deploy time by 60%" }`

**Response** `{ "impact_score": 0.87, "alignment_delta": 0.12 }`

---

#### `POST /canvas/bullet/{bullet_id}/suggest`
Get an AI-generated improvement for a bullet.

**Request** `{ "text": "...", "jd_id": "uuid" }`

**Response** `{ "suggestion": "...", "rationale": "Added quantified metric and aligned to JD keyword 'distributed systems'" }`

---

#### `POST /canvas/bullet/{bullet_id}/accept`
Accept a specific version of a bullet.

**Request** `{ "version": "ai | user | original" }`

**Response** — Updated bullet object.

---

#### `GET /canvas/{resume_id}/export/pdf`
Export resume as a formatted PDF. Returns binary PDF attachment.

---

#### `POST /canvas/section/{section_id}/reoptimize`
Re-run the optimization pipeline on a single section.

**Request** `{ "section_title": "Experience" }`

---

#### `POST /canvas/section/{section_id}/enhance`
Enhance a section with a custom user prompt.

**Request** `{ "section_title": "Skills", "prompt": "Emphasize cloud and DevOps skills" }`

---

#### `POST /canvas/profile/linkedin/refresh`
Trigger a LinkedIn profile delta check.

**Response** `{ "has_changes": true, "items": [...] }`

---

#### `POST /canvas/profile/github/refresh`
Trigger a GitHub profile delta check.

**Response** `{ "has_changes": true, "items": [...] }`

---

#### `POST /canvas/dispute/{bullet_id}`
Dispute an AI-generated bullet. Re-evaluates with the user's reason as context.

**Request** `{ "bullet_text": "...", "reason": "This metric is incorrect" }`

**Response** `{ "new_content": "...", "quality_score": 0.82, "provenance": {...} }`

---

### Interview

#### `GET /interview/{job_id}`
Fetch interview prep data for a completed optimization run.

**Response** — `gaps`, `questions` (behavioral + technical), `talking_points`, `gap_analysis`.

---

#### `POST /interview/{job_id}/generate`
Trigger interview question generation.

**Request** `{ "resume_id": "uuid", "jd_id": "uuid" }`

**Response** `{ "status": "completed" }`

---

#### `POST /interview/question/{question_id}/answer`
Submit a practice answer for AI evaluation.

**Request** `{ "user_answer": "In my last role I led a team of 5 engineers..." }`

**Response**
```json
{
  "score": 78,
  "strengths": ["Good use of STAR structure", "Quantified outcome"],
  "improvements": ["Add more context on the challenge"],
  "improved_answer": "..."
}
```

---

### Job Description

#### `POST /jd/parse`
Parse a raw job description into structured fields.

**Request** `{ "raw_text": "...", "url": "optional" }`

**Response**
```json
{
  "title": "Senior Software Engineer",
  "company": "Acme Corp",
  "keywords": ["Python", "Kubernetes", "distributed systems"],
  "requirements": [...],
  "responsibilities": [...],
  "qualifications": [...]
}
```

---

#### `GET /jd/{jd_id}`
Fetch a previously parsed JD by ID.

---

### Export

#### `POST /export/pdf`
Export resume content as a formatted PDF.

**Request** `{ "content": "...", "filename": "resume_final" }`

**Response** — Binary PDF file download.

---

#### `POST /export/docx`
Export resume content as a DOCX file.

**Request** `{ "content": "...", "filename": "resume_final" }`

**Response** — Binary DOCX file download.

---

### Profile Sync

#### `POST /sync/connect`
Store OAuth access token for GitHub or LinkedIn.

**Request** `{ "platform": "github | linkedin", "access_token": "..." }`

**Response** `{ "platform": "github", "connected": true }`

Requires `GITHUB_CLIENT_ID` or `LINKEDIN_CLIENT_ID` in `.env`.

---

#### `GET /sync/status?user_id={id}`
Get staleness scores and pending delta counts per platform.

**Response**
```json
[
  {
    "platform": "github",
    "last_sync_at": "2026-04-20T10:00:00Z",
    "staleness_score": 0.72,
    "pending_deltas": 3
  }
]
```

---

#### `POST /sync/refresh?platform={p}&job_id={id}&user_id={id}`
Trigger a delta fetch for one platform. Runs SyncAgent, scores deltas against JD embedding, persists new records.

**Response** `{ "deltas_found": 4 }`

---

#### `GET /sync/deltas?user_id={id}`
List pending (unapplied) profile deltas, sorted by relevance score descending.

---

#### `POST /sync/apply/{delta_id}`
Apply a sync delta to the canvas. Routes through GenerationAgent + QualityAgent.

**Request** `{ "job_id": "uuid", "user_id": "uuid" }`

**Response**
```json
{
  "bullet": "Built and open-sourced a Python CLI tool with 200+ GitHub stars",
  "quality_score": 0.88,
  "platform_badge": "github",
  "suggested_section": "Projects",
  "status": "pending"
}
```

---

### Collaborative Review

#### `POST /collab/sessions`
Create a shareable collaborative review session.

**Request** `{ "job_id": "uuid", "owner_id": "uuid" }`

**Response** `{ "shared_token": "abc123", ... }`

---

#### `GET /collab/{token}/session`
Get session metadata using a shared token.

---

#### `GET /collab/{token}/annotations/{bullet_id}`
Fetch all annotations on a specific bullet.

**Response** — Array of annotation objects.

---

#### `POST /collab/{token}/annotations`
Add a mentor/AI annotation to a bullet.

**Request** `{ "bullet_id": "...", "author_id": "uuid", "source": "mentor | ai", "text": "Consider adding the deployment frequency metric here." }`

**Response** — Annotation object with `id`, `created_at`.

---

### Version History

#### `POST /versions/{job_id}/snapshot`
Save a named snapshot of current resume content.

**Request** `{ "content": "...", "label": "After tailoring", "source": "agent | user" }`

**Response** — Snapshot metadata (id, label, source, created_at).

---

#### `GET /versions/{job_id}`
List all snapshots for a run.

**Response** `{ "snapshots": [...], "count": 5 }`

---

#### `GET /versions/{job_id}/diff?v1_id={id}&v2_id={id}`
Token-level diff between two snapshots.

**Response**
```json
{
  "diff": [
    { "type": "same", "text": "Led backend migration" },
    { "type": "remove", "text": "reducing cost" },
    { "type": "add", "text": "reducing infrastructure cost by 40%" }
  ],
  "additions": 4,
  "removals": 2
}
```

---

#### `POST /versions/{job_id}/revert`
Restore resume to a previous snapshot. Creates a new snapshot as revert record (immutable history).

**Request** `{ "version_id": "uuid" }`

**Response** — Restored content + new snapshot metadata.

---

### WebSocket

#### `WS /ws/optimize/{job_id}`
Real-time pipeline event stream.

**Connection flow:**
1. Client connects after calling `POST /optimize`
2. Server reads per-job `asyncio.Queue` populated by `pipeline.py`
3. Each agent emits an event on start and completion
4. `pipeline_complete` event signals end of stream

**Event schema**
```json
{
  "event_type": "agent_start | agent_complete | pipeline_complete | error",
  "agent_name": "ingestion | generation | quality | weak_detection | tailoring | interview | ats",
  "timestamp": "2026-04-23T10:15:30Z",
  "quality_gate_passed": true,
  "quality_score": 0.84,
  "partial_result": {},
  "message": "Quality gate passed with score 0.84"
}
```

---

## Agent Pipeline

**Execution order:**

```
Ingestion
    └─► Generation
            └─► Quality
                    └─► WeakDetection
                              ├─► Tailoring ─┐
                              └─► Interview ─┴─► ATS ─► pipeline_complete
```

Tailoring and Interview run in parallel. ATS runs after both complete.

All agents inherit `BaseAgent`:

| Property | Value |
|---|---|
| `QUALITY_THRESHOLD` | 0.7 |
| `MAX_RETRIES` | 3 |
| Status values | `ok`, `alignment_gate_failed`, `quality_gate_failed` |

---

### Ingestion Agent
**File:** [src/agents/ingestion_agent.py](src/agents/ingestion_agent.py)

Parses the raw resume into structured sections, creates FAISS-indexed segments.

- Regex-based section header detection
- Populates FAISS index with per-bullet segments
- Detects: summary, objective, experience, education, skills, projects, certifications, publications, awards, volunteer, languages
- **Quality score:** ratio of critical sections found (experience, education, skills) / 4

---

### Generation Agent
**File:** [src/agents/generation_agent.py](src/agents/generation_agent.py)

Generates ATS-friendly, impact-driven resume bullets grounded in retrieved context.

- Retrieves top-10 segments from FAISS
- Prompt rules: action verbs (Led, Built, Designed, Implemented...), metrics from source only, 1-2 line bullets, no fabrication
- Tracks retrieved segment IDs and scores as provenance

---

### Quality Agent
**File:** [src/agents/quality_agent.py](src/agents/quality_agent.py)

Two-stage bullet quality enforcement with per-bullet retry.

**Scoring weights per bullet:**
| Signal | Weight |
|---|---|
| Strong action verb | +0.35 |
| Quantified metric | +0.35 |
| Base | +0.30 |
| Weak verb penalty | -0.15 |

**Escalating retry prompts:**
- Attempt 1 — "Lacked quantified metrics…"
- Attempt 2 — "Use format: [Verb] + [Action] + [Result]…"
- Attempt 3 — "Final attempt. ONE bullet, max 20 words, exactly one metric…"

Bullets unresolvable after 3 retries are flagged with a `unresolvable` warning.

---

### Weak Detection Agent
**File:** [src/agents/weak_detection_agent.py](src/agents/weak_detection_agent.py)

Identifies ATS coverage gaps and weak language patterns.

- Keyword gap analysis: JD words absent from resume
- Section completeness check
- Vague bullet detection (< 30 chars)
- RAG alignment check (segments scoring < 0.5)
- **Quality score:** `0.6 + len(weaknesses) * 0.05`, capped at 1.0

---

### Tailoring Agent
**File:** [src/agents/tailoring_agent.py](src/agents/tailoring_agent.py)

Rewrites resume content to align with a specific job description. Has a hard alignment gate.

**Alignment Gate:**
- Computes cosine similarity (SBERT) between resume and JD embeddings
- Threshold: **0.6**
- If below: returns `status = "alignment_gate_failed"` with three weakest sections ranked by distance — no LLM call made

**Tailoring logic:**
- Industry profile classification (tech_swe / finance / academia / consulting / product / data_science)
- JD keyword integration (natural, not keyword-stuffed)
- Experience reordering to front-load JD-relevant roles
- Anti-fabrication rule enforced in system prompt
- Output: Markdown with `##` sections and `-` bullets

---

### Interview Agent
**File:** [src/agents/interview_agent.py](src/agents/interview_agent.py)

Generates structured interview prep materials from the optimized resume + JD.

**Output includes:**
- 5-7 Behavioral questions (STAR framework: leadership, conflict, decisions, failure, collaboration)
- 5-7 Technical questions (technology/seniority-specific)
- 3-5 Talking points tied to high-impact resume achievements
- 3-5 Questions to ask the interviewer

All answers grounded in actual resume data; no fabrication.

---

### ATS Agent
**File:** [src/agents/ats_agent.py](src/agents/ats_agent.py)

Simulates resume parsing through 4 real ATS platforms.

| Platform | Max Bullet | Disallowed Chars | Weight |
|---|---|---|---|
| Workday | 200 chars | `• → ★` | 0.30 |
| Greenhouse | 250 chars | `→ ★` | 0.25 |
| Lever | 300 chars | — | 0.25 |
| Taleo | 180 chars | `• → ★ \|` | 0.20 |

Per platform: checks required sections, character limits, disallowed symbols, keyword match rate.

**Weighted ATS score** = `Σ (parse_accuracy × platform_weight)`

Quality threshold: 0.0 — ATS agent is advisory only, never blocks the pipeline.

---

### Sync Agent
**File:** [src/agents/sync_agent.py](src/agents/sync_agent.py)

Fetches incremental GitHub/LinkedIn profile updates and scores them against the JD.

**GitHub flow:** Fetches repos via GitHub API (sorted by updated, cursor-based pagination), item type = `repository`

**LinkedIn flow:** Fetches positions and skills via LinkedIn API v2 (OAuth 2.0, `r_liteprofile` scope), item types = `role`, `skill`

**Scoring:** Embeds each item → cosine similarity vs JD embedding → filters at threshold 0.5 → classifies into suggested resume section

---

## RAG System

### Embedder
**File:** [src/rag/embedder.py](src/rag/embedder.py)

| Model | Use case | Dimensions |
|---|---|---|
| `all-MiniLM-L6-v2` | English (default) | 384 |
| `paraphrase-multilingual-MiniLM-L12-v2` | 50+ languages | 384 |

- Language auto-detected via `langdetect`; switches to multilingual if non-English
- Batch encoding (`batch_size=32`)
- L2-normalized output for cosine similarity via inner product

---

### Vector Store
**File:** [src/rag/vector_store.py](src/rag/vector_store.py)

- One FAISS `IndexFlatIP` index per `user_id`
- Persisted to `./data/faiss_indices/{user_id}.index`
- Auto-loaded from disk on first access
- Methods: `get_or_create_index`, `add_vectors`, `search`, `save_index`, `delete_index`

---

### Retriever
**File:** [src/rag/retriever.py](src/rag/retriever.py)

High-level RAG orchestration on top of the vector store.

- `index_segments(segments)` — embed and store a list of segment dicts
- `retrieve(query, top_k=5)` — semantic search → list of `RetrievedSegment`
- `retrieve_by_section(query, section, top_k=5)` — filter by section name
- `get_stats()` — total vectors, dimension, metadata count

**Segment schema:**
```python
{ "content": str, "segment_id": str, "section": str, "index": int }
```

---

### Alignment Scorer
**File:** [src/scoring/alignment.py](src/scoring/alignment.py)

- Encodes all resume lines and JD requirements
- Builds full similarity matrix (JD × resume)
- **Overall score:** average of best-match per JD requirement
- **Section scores:** per-section averages
- **Gaps:** JD requirements with best match < 0.5

---

## Database Schema

All tables use UUID primary keys (`String`, generated server-side).

---

### `users`
| Column | Type | Notes |
|---|---|---|
| `id` | String (UUID) | PK |
| `email` | String | Unique, indexed |
| `created_at` | DateTime | UTC |

---

### `resumes`
| Column | Type | Notes |
|---|---|---|
| `id` | String (UUID) | PK |
| `user_id` | String | FK → users.id, nullable |
| `filename` | String | Nullable |
| `raw_text` | Text | Required |
| `created_at` | DateTime | UTC |

---

### `optimization_runs`
| Column | Type | Notes |
|---|---|---|
| `id` | String (UUID) | PK |
| `resume_id` | String | FK → resumes.id, nullable |
| `job_description` | Text | Required |
| `status` | String | `queued \| running \| completed \| failed` |
| `celery_job_id` | String | Nullable, indexed |
| `result_json` | JSON | Full agent outputs |
| `created_at` | DateTime | UTC |
| `completed_at` | DateTime | Nullable |

---

### `profile_sync_states`
| Column | Type | Notes |
|---|---|---|
| `id` | String (UUID) | PK |
| `user_id` | String | FK → users.id, indexed |
| `platform` | String(20) | `github \| linkedin` |
| `last_sync_at` | DateTime | Nullable |
| `access_token` | Text | Encrypted (Fernet) |
| `sync_cursor` | String | Pagination cursor |
| `staleness_score` | Float | Default 1.0 |
| `created_at` | DateTime | UTC |
| `updated_at` | DateTime | Auto-updated |

---

### `sync_deltas`
| Column | Type | Notes |
|---|---|---|
| `id` | String (UUID) | PK |
| `user_id` | String | FK → users.id, indexed |
| `platform` | String(20) | |
| `item_type` | String(30) | `repository \| role \| skill \| certification` |
| `title` | Text | Required |
| `description` | Text | Nullable |
| `relevance_score` | Float | Cosine similarity to JD |
| `suggested_section` | String(50) | `Experience \| Projects \| Skills` |
| `raw_data` | JSON | Full API response |
| `applied` | Boolean | Default False |
| `detected_at` | DateTime | UTC |
| `applied_at` | DateTime | Nullable |

---

### `collab_sessions`
| Column | Type | Notes |
|---|---|---|
| `id` | String (UUID) | PK |
| `job_id` | String | Indexed |
| `owner_id` | String | Creator user |
| `shared_token` | String | Unique, indexed |
| `created_at` | DateTime | UTC |

---

### `mentor_annotations`
| Column | Type | Notes |
|---|---|---|
| `id` | String (UUID) | PK |
| `session_id` | String | FK → collab_sessions.id, indexed |
| `bullet_id` | String | Which bullet |
| `author_id` | String | Who left the comment |
| `role` | String(20) | `viewer \| commenter \| editor` (default: `commenter`) |
| `source` | String(10) | `mentor \| ai` (default: `mentor`) |
| `text` | Text | Annotation content |
| `created_at` | DateTime | UTC |

---

## Parsers & Scoring

### Resume Parser
**File:** [src/parsers/resume_parser.py](src/parsers/resume_parser.py)

| Format | Library |
|---|---|
| PDF | PyPDF2 |
| DOCX / DOC | python-docx |
| TXT | Built-in (UTF-8 with fallback) |

Raises `ParsingError` if output < 50 characters or format unsupported.

---

### JD Parser
**File:** [src/parsers/jd_parser.py](src/parsers/jd_parser.py)

Regex-based extraction:
- **Title:** First non-empty line < 100 chars
- **Requirements / Responsibilities / Qualifications:** Pattern-matched headers
- **Skills:** Hardcoded tech keyword patterns (Python, React, TypeScript, AWS, Docker, etc.)
- **Keywords:** Top-30 most frequent non-stop-words

---

### Impact Scorer
**File:** [src/scoring/impact_scorer.py](src/scoring/impact_scorer.py)

Per-bullet scoring:

| Signal | Weight |
|---|---|
| Base | +0.30 |
| Strong action verb | +0.25 |
| Quantified metric (`\d+`) | +0.25 |
| Length > 30 chars | +0.10 |
| Technical terms / proper nouns | +0.10 |
| Weak verb penalty | -0.15 |

Returns: `overall_score`, per-bullet scores, summary (totals with/without metrics, high/low impact counts).

---

## Config & Industry Profiles

### Settings
**File:** [src/config/settings.py](src/config/settings.py)

Loaded from `.env` via `pydantic-settings`:

| Key | Default |
|---|---|
| `OPENAI_API_KEY` | — |
| `LLM_PROVIDER` | `openai` |
| `DATABASE_URL` | `postgresql://...` |
| `REDIS_URL` | `redis://localhost:6379` |
| `FAISS_INDEX_DIR` | `./data/faiss_indices` |
| `APP_ENV` | `development` |
| `APP_PORT` | `8000` |

---

### Industry Profiles
**File:** [src/config/industry_profiles.py](src/config/industry_profiles.py)

Auto-classified from JD keywords. Defaults to `tech_swe`.

| Profile | Tone | Max Pages | Scoring Weights (impact / alignment / coverage / ats) |
|---|---|---|---|
| `tech_swe` | Impact-driven, metric-heavy | 1 | 0.40 / 0.30 / 0.20 / 0.10 |
| `finance` | Formal, quantified, compliance-aware | 2 | 0.50 / 0.25 / 0.15 / 0.10 |
| `academia` | Formal, publication-aware, comprehensive | 5 | 0.20 / 0.30 / 0.40 / 0.10 |
| `consulting` | Concise, client-impact language | 1 | 0.45 / 0.30 / 0.15 / 0.10 |
| `product` | User-outcome focused, roadmap-aware | 1 | 0.40 / 0.35 / 0.15 / 0.10 |
| `data_science` | Analytical, experiment-driven | 2 | 0.35 / 0.30 / 0.25 / 0.10 |

---

## Frontend — Pages

**Base path:** `frontend/src/pages/`

### HomePage
**Route:** `/`

Marketing / landing page.

- Animated cycling hero words: "Optimized", "Transformed", "Tailored", "Elevated"
- Mouse-glow parallax effect (cursor-following div)
- Scroll-reveal via `IntersectionObserver`
- Animated CTA button (conic gradient ring on hover via `requestAnimationFrame`)
- Feature cards: ATS alignment, Interview Prep, GitHub/LinkedIn sync

---

### OptimizePage
**Route:** `/optimize`

Resume upload and JD entry — the entry point to the pipeline.

**Features:**
- Drag-and-drop file upload (PDF, DOCX, TXT)
- PDF text extraction via `pdf.js` (v3.x, CDN worker)
- File size limit: 10 MB
- JD paste textarea
- Optional inputs: LinkedIn URL, GitHub URL, candidate name
- Industry profile selector (auto-detect or manual)
- Character count and file size display

**State:** `uploadState`, `fileName`, `fileSize`, `resumeText`, `candidateName`, `jdText`, `linkedinUrl`, `githubUrl`, `isOptimizing`, `error`, `industryProfile`

**On submit:** Calls `POST /optimize` → redirects to `/canvas/{job_id}`

---

### CanvasPage
**Route:** `/canvas/:resumeId`

The main interactive resume editor. Three-panel layout:

| Panel | Content |
|---|---|
| Left (collapsible) | JD reference |
| Center | Resume with editable bullets |
| Right | Metrics, scoring, version timeline |

**Features:**
- Inline bullet editing with AI suggestion overlay
- Accept / reject AI suggestions per bullet
- Section-level re-optimization
- Custom enhancement prompts
- GitHub / LinkedIn profile refresh (ProfileSyncPanel)
- Version history and one-click rollback (VersionTimeline)
- Provenance tooltips (WhyButton)
- Dispute mechanism for AI-generated content
- Export to PDF

---

### InterviewPage
**Route:** `/interview/:jobId`

Interview preparation workspace.

**Features:**
- Gap analysis with severity colors (high / medium / low)
- Categorized questions: Technical, Behavioral, Role-specific, Company-specific
- Difficulty levels: Easy, Medium, Hard
- Talking points and STAR framework answer structures
- "Why this question?" context per question
- Practice mode: User types answer → receives scored AI feedback (score 0-100, strengths, improvements, improved answer)
- Category filtering tabs

---

### ResultsPage
**Route:** `/results/:jobId`

Optimization results summary.

Displays: overall alignment score, keyword coverage, impact score, ATS pass rate, agent-level outputs. *(Implementation in progress — see PROJECT_STATUS.md)*

---

## Frontend — Components

**Base path:** `frontend/src/components/`

| Component | Purpose |
|---|---|
| `AlignmentGauge` | Visual gauge for resume-JD alignment score (0–1) |
| `Button` | Styled button with conic ring animation on hover |
| `Card` | Reusable card container |
| `Footer` | Site footer |
| `KeywordChips` | Matched / unmatched keyword chips |
| `LoadingSpinner` | Animated loading indicator |
| `MentorAnnotationPanel` | View and add mentor comments per bullet; groups by `bullet_id` |
| `Navbar` | Navigation header with logo, links, CTA |
| `PdfUploadZone` | Drag-and-drop area with validation and progress display |
| `ProfileSyncPanel` | GitHub/LinkedIn refresh controls; shows staleness score + pending deltas |
| `ResumePreview` | Inline resume rendering inside CanvasPage |
| `ScoreBadge` | Small badge showing impact or quality score |
| `StalenessIndicator` | Profile freshness status (updated / stale / very stale) |
| `SuggestionList` | Bullet suggestion list with accept/reject actions |
| `VersionTimeline` | Chronological snapshot list with source labels and rollback |
| `WeaknessCard` | Weakness title, impact level, and suggested fix |
| `WhyButton` | Provenance tooltip — shows `decision_rationale`, retrieved chunks, confidence |

---

## Frontend — State Management

**Library:** Zustand with `persist` middleware (survives page refresh)

### Canvas Store
**File:** [frontend/src/stores/canvasStore.ts](frontend/src/stores/canvasStore.ts)

**State**

| Field | Type | Description |
|---|---|---|
| `canvasState` | Enum | `EMPTY \| LOADED \| IDLE \| OPTIMIZING \| OPTIMIZED \| RE_OPTIMIZING \| EDITING \| ERROR` |
| `resume` | Resume \| null | Full resume object |
| `jd` | ParsedJD \| null | Parsed job description |
| `metrics` | Metrics | alignment, keywordCoverage, impactScore, atsPassRate |
| `pipeline` | PipelineState | agents dict, currentAgent, isRunning |
| `keywords` | KeywordItem[] | keyword, matched, source |
| `changes` | ChangeData[] | before/after pairs, source, timestamp |
| `events` | string[] | Pipeline event log |
| `editingBulletId` | string \| null | Active edit target |
| `bulletUndoStacks` | Record<string, UndoEntry[]> | Per-bullet undo history with timestamps |
| `bulletProvenance` | Record<string, BulletProvenance> | agent_name, decision_rationale, confidence |

**Key actions:** `updateBullet`, `undoBullet`, `addVersion`, `setBulletProvenance`, `setAgentState`, `reset`

---

## Infrastructure

### Docker Services

**docker-compose.yml** (production)

| Service | Image | Port | Notes |
|---|---|---|---|
| `backend` | Custom (FastAPI) | 8000 | Depends on postgres + redis; FAISS volume mounted |
| `postgres` | postgres:16-alpine | 5432 | Healthcheck: `pg_isready` every 5s |
| `redis` | redis:7-alpine | 6379 | Broker for Celery |

Volumes: `postgres_data` (persistent DB), `faiss_data` (persistent FAISS indices)

Network: `resume-intel-net` (bridge)

**docker-compose.dev.yml** — Mounts `./src`, `./tests`, `./alembic` for live-reload development.

---

### Alembic (Database Migrations)

```bash
# Apply all pending migrations
docker compose exec backend alembic upgrade head

# Generate a new migration from model changes
docker compose exec backend alembic revision --autogenerate -m "add collab sessions"

# Roll back one migration
docker compose exec backend alembic downgrade -1
```

---

### Running Locally

```bash
# Backend
cp .env.example .env        # fill in keys
pip install -e ".[dev]"
uvicorn src.api:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev

# Tests
pytest tests/ -v
ruff check src/ --fix && ruff format src/
```

---

## Dependencies

**Backend core**

| Package | Purpose |
|---|---|
| `fastapi >= 0.104` | API framework |
| `uvicorn[standard]` | ASGI server |
| `celery[redis] >= 5.3` | Async background tasks |
| `pydantic >= 2.5` | Schema validation |
| `sqlalchemy >= 2.0` | ORM |
| `alembic` | Database migrations |
| `psycopg2-binary` | PostgreSQL driver |
| `redis` | Cache and Celery broker |
| `openai >= 1.6` | LLM API |
| `sentence-transformers >= 2.2` | SBERT embeddings |
| `faiss-cpu >= 1.7` | Vector index |
| `langdetect >= 1.0` | Language detection |
| `numpy`, `scikit-learn >= 1.3` | Numeric computation |
| `pypdf2` | PDF parsing |
| `python-docx` | DOCX parsing |
| `structlog` | Structured logging |
| `httpx` | Async HTTP client |
| `cryptography >= 41` | OAuth token encryption |

**Dev tooling:** `pytest`, `pytest-asyncio`, `pytest-cov`, `ruff`, `mypy`
