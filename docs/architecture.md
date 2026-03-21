# System Architecture

## Overview

Resume Intel is a Multi-Agent Resume & Career Intelligence System that combines six specialized AI agents with Retrieval-Augmented Generation (RAG) to parse, analyze, optimize, and tailor resumes. The system follows a layered architecture with clear separation of concerns.

## 4-Layer Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                           │
│                                                                 │
│   React 18 + TypeScript          Tailwind CSS                   │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐     │
│   │ Resume       │  │ Optimization │  │ Interview Prep   │     │
│   │ Upload UI    │  │ Dashboard    │  │ Panel            │     │
│   └──────────────┘  └──────────────┘  └──────────────────┘     │
│   React Query for server state    │   WebSocket for live status │
├─────────────────────────────────────────────────────────────────┤
│                       API LAYER                                 │
│                                                                 │
│   FastAPI (Python 3.11+)                                        │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐     │
│   │ /api/v1/     │  │ Auth         │  │ Rate Limiter     │     │
│   │ resume/*     │  │ Middleware   │  │ (sliding window) │     │
│   │ optimize/*   │  │ (JWT)        │  │                  │     │
│   │ interview/*  │  │              │  │                  │     │
│   └──────────────┘  └──────────────┘  └──────────────────┘     │
│   Pydantic v2 request/response models  │  Background workers   │
├─────────────────────────────────────────────────────────────────┤
│                   INTELLIGENCE LAYER                            │
│                                                                 │
│   Agent Pipeline (Sequential)                                   │
│   ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌───────────┐ │
│   │Ingest│→│ Gen  │→│ QA   │→│ Weak │→│Tailor│→│ Interview │ │
│   │Agent │ │Agent │ │Agent │ │Detect│ │Agent │ │ Agent     │ │
│   └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └───────────┘ │
│                                                                 │
│   RAG Engine                                                    │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐     │
│   │ SBERT        │  │ FAISS        │  │ Context Builder  │     │
│   │ Encoder      │  │ IVF-PQ Index │  │ & Ranker         │     │
│   └──────────────┘  └──────────────┘  └──────────────────┘     │
├─────────────────────────────────────────────────────────────────┤
│                      DATA LAYER                                 │
│                                                                 │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐     │
│   │ PostgreSQL   │  │ FAISS        │  │ Redis            │     │
│   │ (relational) │  │ (vectors)    │  │ (cache + queue)  │     │
│   │              │  │              │  │                  │     │
│   │ users        │  │ per-user     │  │ session store    │     │
│   │ resumes      │  │ index files  │  │ job status       │     │
│   │ jobs         │  │ (.index)     │  │ rate limit       │     │
│   │ opt_runs     │  │              │  │ counters         │     │
│   │ segments     │  │              │  │                  │     │
│   └──────────────┘  └──────────────┘  └──────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

### Resume Upload and Optimization Flow

```
User uploads resume (PDF/DOCX)
        │
        ▼
┌─────────────────┐
│  API Gateway     │──── Auth check (JWT) ──── Rate limit check
│  POST /upload    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  File Parser     │──── Extract raw text from PDF/DOCX
│  (pdfplumber /   │
│   python-docx)   │
└────────┬────────┘
         │  raw text + metadata
         ▼
┌─────────────────┐
│  IngestionAgent  │──── Segment into sections (experience, education, skills...)
└────────┬────────┘
         │  ResumeSegments
         ▼
┌─────────────────┐
│  RAG Engine      │──── Embed segments with SBERT
│  (Index Phase)   │──── Store vectors in per-user FAISS index
└────────┬────────┘
         │  indexed segments
         ▼
┌─────────────────┐
│  Store to DB     │──── PostgreSQL: resume record + segment rows
└─────────────────┘

User requests optimization (POST /optimize with job_id + JD)
        │
        ▼
┌─────────────────┐
│  Background Task │──── Celery worker picks up job
│  (Redis queue)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐    ┌─────────────────┐
│  RAG Engine      │───►│  Retrieve top-k  │
│  (Query Phase)   │    │  relevant chunks │
└────────┬────────┘    └─────────────────┘
         │  context chunks
         ▼
┌─────────────────┐
│  GenerationAgent │──── Generate optimized bullet points using LLM + context
└────────┬────────┘
         │  optimized bullets
         ▼
┌─────────────────┐
│  QualityAgent    │──── Score each bullet (threshold: 0.7)
│                  │──── Retry if below threshold (max 3 retries)
└────────┬────────┘
         │  quality-passed bullets
         ▼
┌─────────────────┐
│ WeakDetection    │──── Identify weak areas (vague language, missing metrics)
│ Agent            │
└────────┬────────┘
         │  weakness annotations
         ▼
┌─────────────────┐
│  TailoringAgent  │──── Align resume content to target JD
│                  │──── Alignment threshold: 0.6
└────────┬────────┘
         │  tailored resume
         ▼
┌─────────────────┐
│  InterviewAgent  │──── Generate interview prep based on resume + JD
└────────┬────────┘
         │  interview questions + talking points
         ▼
┌─────────────────┐
│  Store Results   │──── Write optimization_run record to PostgreSQL
│  Update Status   │──── Set job status to COMPLETED in Redis
└─────────────────┘
```

## Agent Pipeline Interfaces

Each agent implements a common `BaseAgent` interface:

```
BaseAgent
├── name: str
├── async execute(input: AgentInput) -> AgentOutput
├── async validate(output: AgentOutput) -> bool
└── retry_policy: RetryPolicy(max_retries=3, backoff=exponential)
```

Pipeline composition:

```
Pipeline.create([
    IngestionAgent,
    GenerationAgent,
    QualityAgent,
    WeakDetectionAgent,
    TailoringAgent,
    InterviewAgent,
]) -> PipelineExecutor
```

The pipeline executor passes each agent's output as the next agent's input. If any agent fails validation after exhausting retries, the pipeline halts and the job is marked as FAILED with a diagnostic message.

## RAG Retrieval Flow

```
Query (JD text or optimization prompt)
        │
        ▼
┌─────────────────┐
│  SBERT Encoder   │──── all-MiniLM-L6-v2 (384 dimensions)
│  Encode query    │
└────────┬────────┘
         │  query vector (384-d)
         ▼
┌─────────────────┐
│  FAISS Search    │──── IVF-PQ index (nlist=100, M=16, nbits=8)
│  (per-user idx)  │──── nprobe=10 at query time
└────────┬────────┘
         │  top-k candidate IDs + distances
         ▼
┌─────────────────┐
│  Re-ranker       │──── Cross-encoder re-ranking on top-k
│  (optional)      │
└────────┬────────┘
         │  ranked results
         ▼
┌─────────────────┐
│  Context Builder │──── Assemble prompt context from ranked segments
│                  │──── Respect token budget (max 2048 context tokens)
└─────────────────┘
```

## Database Schema Overview

### `users`
| Column       | Type         | Description                  |
|-------------|-------------|------------------------------|
| id          | UUID (PK)   | Primary key                  |
| email       | VARCHAR(255)| Unique, indexed              |
| password_hash| VARCHAR    | bcrypt hashed password       |
| created_at  | TIMESTAMP   | Account creation time        |
| updated_at  | TIMESTAMP   | Last modification            |

### `resumes`
| Column       | Type         | Description                  |
|-------------|-------------|------------------------------|
| id          | UUID (PK)   | Primary key                  |
| user_id     | UUID (FK)   | References users.id          |
| filename    | VARCHAR(255)| Original upload filename     |
| raw_text    | TEXT        | Extracted plain text         |
| file_hash   | VARCHAR(64) | SHA-256 for deduplication    |
| parsed_at   | TIMESTAMP   | When parsing completed       |
| created_at  | TIMESTAMP   | Upload time                  |

### `jobs`
| Column       | Type         | Description                  |
|-------------|-------------|------------------------------|
| id          | UUID (PK)   | Primary key                  |
| user_id     | UUID (FK)   | References users.id          |
| title       | VARCHAR(255)| Job title                    |
| company     | VARCHAR(255)| Target company               |
| description | TEXT        | Full job description text    |
| created_at  | TIMESTAMP   | When JD was added            |

### `optimization_runs`
| Column       | Type         | Description                  |
|-------------|-------------|------------------------------|
| id          | UUID (PK)   | Primary key                  |
| user_id     | UUID (FK)   | References users.id          |
| resume_id   | UUID (FK)   | References resumes.id        |
| job_id      | UUID (FK)   | References jobs.id           |
| status      | ENUM        | PENDING/RUNNING/COMPLETED/FAILED |
| result_json | JSONB       | Full pipeline output         |
| quality_score| FLOAT      | Overall quality score        |
| alignment_score| FLOAT    | JD alignment score           |
| started_at  | TIMESTAMP   | Pipeline start time          |
| completed_at| TIMESTAMP   | Pipeline completion time     |
| error_message| TEXT       | Error details if FAILED      |
| created_at  | TIMESTAMP   | Record creation time         |

### `segments`
| Column       | Type         | Description                  |
|-------------|-------------|------------------------------|
| id          | UUID (PK)   | Primary key                  |
| resume_id   | UUID (FK)   | References resumes.id        |
| section_type| VARCHAR(50) | experience/education/skills/projects/summary |
| content     | TEXT        | Segment text content         |
| embedding_id| VARCHAR(64) | Reference to FAISS vector ID |
| position    | INTEGER     | Order within the resume      |
| created_at  | TIMESTAMP   | When segment was created     |

### Entity Relationship Summary

```
users 1──────N resumes
users 1──────N jobs
users 1──────N optimization_runs
resumes 1────N segments
resumes 1────N optimization_runs
jobs 1───────N optimization_runs
```
