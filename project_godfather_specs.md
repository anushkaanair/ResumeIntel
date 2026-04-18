# Resume Intel — Project Godfather Specifications

This document serves as the absolute source of truth and blueprint (Godfather file) for the **Resume Intel** system. It encompasses the system's architecture, frontend and backend tech stacks, multi-agent AI pipeline details, API endpoints, testing conventions, and UI component specifications. 

---

## 1. Project Overview

**Resume Intel** is an AI-powered, multi-agent resume optimization and career intelligence platform. Users upload a resume (PDF/DOCX/TXT) or paste text, provide a target Job Description (JD), and the system utilizes a 6-agent sequential AI pipeline to:
1. Parse and segment the resume.
2. Generate optimized, metrics-driven bullet points via RAG-grounding.
3. Enforce quality standards (scoring >= 0.7) and avoid hallucinations.
4. Detect weaknesses and employment gaps.
5. Tailor the content to a specific JD (`alignment gate` >= 0.6).
6. Generate interview preparation materials (Behavioral & Technical).

**Key Architectures:**
- **Multi-Agent Pipeline** instead of Monolithic LLM (for modularity, debugging, and independent tuning).
- **RAG-Grounded Generation:** Enforcing that every piece of output traces back to the source parametric memory. 
- **Agent Flow:** Ingestion -> Generation -> Quality -> WeakDetection -> Tailoring -> (Parallel) Interview.

---

## 2. Tech Stack & Dependencies

### Backend
- **Core language:** Python 3.11+
- **Framework:** FastAPI >= 0.104
- **Async Execution / Worker Tasks:** Celery >= 5.3 with Redis broker
- **Vector DB / RAG:** FAISS (IVF-PQ, 384-dim) & `sentence-transformers` (`all-MiniLM-L6-v2`)
- **Database Layer:** PostgreSQL 16 mapped via SQLAlchemy 2.0 & Alembic
- **Caching:** Redis 7
- **LLM Interface:** GPT-4o via OpenAI SDK (`openai >= 1.6`)
- **Parsers:** `pypdf2`, `python-docx`, `python-multipart`
- **Validation:** Pydantic >= 2.5, Pydantic-settings
- **Linting & Testing:** Ruff, MyPy, Pytest + Pytest-asyncio

### Frontend
- **Core Library:** React 18 
- **Language / Types:** TypeScript 5.3.3
- **Build tool:** Vite 5.0.8 
- **Router:** React-Router-DOM 6.21.0
- **Styling:** TailwindCSS 3.4.0, Autoprefixer, PostCSS
- **Animations:** Framer Motion 10.18.0
- **API Client:** Axios 1.6.0
- **State Management:** Zustand 4.5.7
- **UI Components & Icons:** Lucide React
- **PDF Extraction:** `pdfjs-dist` (3.11.174)

---

## 3. Directory Map & Rules

```text
resume-intel/
│
├── .claude/               # Configurations, permissions, and skill prompts 
├── docs/                  # Architectural references & Agent specifications 
├── src/                   # Python FastAPI Backend Source Code
│   ├── agents/            # BaseAgent inheritance schemas + 6 agent logic (Ingest, Generate, Tailor, etc.)
│   ├── api/               # FastAPI endpoints mapped by resource (routes/ & schemas/)
│   ├── parsers/           # Resume + JD mapping and structure
│   ├── rag/               # Vector Store, Embedder, and Retriever
│   ├── scoring/           # Impact scorer & Alignment modules
│   └── config/            # Pydantic Settings implementation
├── frontend/              # React TypeScript Frontend
│   ├── src/components/    # Reusable standardized UI blocks (Gauges, buttons, cards)
│   ├── src/hooks/         # useJobStatus, useOptimize custom interactions
│   ├── src/pages/         # Functional react pages (Home, Optimize, Results, InterviewPrep)
│   └── src/lib/           # Axios interceptors, constants, API interactions
├── tests/                 # Shared PyTest endpoints, Agent Unit Tests, RAG Mock tests
├── pyproject.toml         # Backend packaging
└── docker-compose.yml     # DB/Redis deployment stack
```

---

## 4. Multi-Agent Pipeline Specs

Every Agent under `src/agents/` must inherit from `BaseAgent` and enforce these capabilities:
1. `execute(input: AgentInput) -> AgentOutput`
2. `validate_input(...)` and `validate_output(...)`
3. Include an internal pipeline `retriever.retrieve(query, top_k)` to supply RAG-context BEFORE calling the LLM.
4. Have strict Quality Threshold parameters (e.g. `QUALITY_THRESHOLD = 0.7`) to enforce retry capabilities (up to 3x) if generations don't meet minimum viable states.

*Important Constraint*: Never fabricate metrics, experience, or achievements. Ensure endpoints operate optimally (around 200ms per sync) and mask all underlying PII.

---

## 5. Endpoints Reference & Schemas

### `/api/v1/resume/upload` [POST]
Uploads a Resume to trigger parsing:
- Request: `multipart/form-data` with `file`
- Validation: Limit 5MB. Accepts `.pdf`, `.doc`, `.docx`, `.txt`. 

### `/api/v1/optimize` [POST]
Kicks off the Optimization Pipeline
- Body: `{"resume_text": "...", "job_description": "..." }`
- Response: `{"status": "ok", "data": {"job_id": "uuid-...", "message": "Pipeline started"}}`

### `/api/v1/optimize/{job_id}/status` & `/result` [GET]
Checks job execution & fetches structured data output.
- Responses contain agent-by-agent breakdowns: `ingestion`, `generation`, `quality`, `weak_detection`, `tailoring`, `interview`.

---

## 6. Frontend UI Components & Status

### Components Built Validating Frontend Spec
- `Button.tsx`: Variants of primary (`bg-blue-600`), secondary, & ghost.
- `Card.tsx`: Standard UI overlay component with fade-ins.
- `AlignmentGauge.tsx`: Visual circle showing Resume alignment.
- `PdfUploadZone.tsx`: Handles file drop & drag scenarios, passes binary data to Backend.
- Custom Hooks: `useJobStatus` and `useOptimize` for reactive polling patterns.

### Navigation / Router Map
- `/` (`HomePage`): Needs complete restructure to present an appealing landing page.
- `/optimize` (`OptimizePage`): Operational page where upload & copy/pasting happens.
- `/results/:jobId` (`ResultsPage`): Detailed dashboard displaying optimized resume blocks, badges, quality graphs.
- `/dashboard` (TODO): Historical iterations and tracking.
- `/interview/:jobId` (TODO): Expanding on QA test banks.

## 7. Testing Environments

All API Endpoint & agent components tests operate via AAA flow (`Arrange`, `Act`, `Assert`):
- `pytest tests/ -v`
- Mock all LLM external dependencies and avoid network transactions on unit scopes.
- Frontend builds and previews through `npm run preview`.

---

**End of Global Specifications**
