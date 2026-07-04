
<h1>ResumeIntel</h1>
<p><strong>AI-Powered Multi-Agent Resume Optimization & Career Intelligence System</strong></p>
<p>
  <a href="https://github.com/anushkaanair/ResumeIntel"><img src="https://img.shields.io/badge/GitHub-ResumeIntel-181717?style=flat&logo=github" alt="GitHub"/></a>
  <a href="mailto:anushkanair93@gmail.com"><img src="https://img.shields.io/badge/Contact-anushkanair93%40gmail.com-EA4335?style=flat&logo=gmail&logoColor=white" alt="Email"/></a>
  <a href="https://linkedin.com/in/anushka-nair"><img src="https://img.shields.io/badge/LinkedIn-Anushka_Nair-0A66C2?style=flat&logo=linkedin&logoColor=white" alt="LinkedIn"/></a>
</p>
<p>
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/FastAPI-0.111-009688?style=flat&logo=fastapi&logoColor=white"/>
  <img src="https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react&logoColor=black"/>
  <img src="https://img.shields.io/badge/TypeScript-5.0-3178C6?style=flat&logo=typescript&logoColor=white"/>
  <img src="https://img.shields.io/badge/FAISS-Vector_Search-FF6F00?style=flat"/>
  <img src="https://img.shields.io/badge/Celery_+_Redis-Task_Queue-37814A?style=flat"/>
  <img src="https://img.shields.io/badge/Docker-Containerized-2496ED?style=flat&logo=docker&logoColor=white"/>
  <img src="https://img.shields.io/badge/Patent-Pending_%7C_13_Claims-8A2BE2?style=flat"/>
</p>
<p><em>Patent filed under The Patents Act, 1970 (India) · 13 Claims · 5 Novel Inventive Steps</em></p>
<p>
  <a href="#-what-is-resumeintel">Overview</a> ·
  <a href="#-the-7-agent-pipeline">Architecture</a> ·
  <a href="#-novel-inventive-steps">Novelty</a> ·
  <a href="#-tech-stack">Tech Stack</a> ·
  <a href="#-setup">Setup</a> ·
  <a href="#-api-reference">API</a> ·
  <a href="#-patent-information">Patent</a>
</p>
</div>

🧠 What is ResumeIntel?

ResumeIntel is a production-grade, multi-agent AI system that transforms raw candidate resumes into ATS-optimized, interview-ready career documents — grounded entirely in the candidate's own verified experience.
Unlike existing tools (Jobscan, Rezi, Resume.io) that generate content from parametric model memory and risk hallucinating metrics or achievements, ResumeIntel mandates SBERT + FAISS retrieval before every LLM generation call — making every improvement traceable to something the candidate actually did.
The system coordinates seven specialized autonomous agents, implements real-time agent observability over WebSocket, and contains five architecturally novel mechanisms currently under patent review.

📄 Patent Status: Provisional/Complete Specification filed under The Patents Act, 1970 & The Patent Rules, 2003 — 13 claims, 5 novel inventive steps with no identified prior art.


**🏗️ The 7-Agent Pipeline
**

┌────────────────────────────────────────────────────────────────────┐
│                      ResumeIntel Pipeline                          │
│                                                                    │
│  [Resume PDF/DOCX + Job Description]                               │
│              │                                                     │
│              ▼                                                     │
│  ┌───────────────┐   ┌─────────────────┐   ┌──────────────────┐    │
│  │   Agent 1     │──▶│    Agent 2      │──▶│    Agent 3       │   │
│  │  Ingestion    │   │   Generation    │   │    Quality       │    │
│  │  Parse ·      │   │  FAISS-grounded │   │  3-stage retry   │    │
│  │  Normalize    │   │  bullet writes  │   │  score ≥ 0.7     │    │
│  └───────────────┘   └─────────────────┘   └──────────────────┘    │
│                                                      │             │
│                         ┌────────────────────────────┘             │
│                         ▼                                          │
│  ┌────────────────┐   ┌──────────────────┐                         │
│  │   Agent 4      │   │    Agent 5       │                         │
│  │  Weak Detect.  │   │    Tailoring     │                         │
│  │  Vague · gaps  │   │  Align gate      │                         │
│  │  skill miss    │   │  cosine ≥ 0.6    │                         │
│  └────────────────┘   └──────────────────┘                         │
│                                │                                   │
│           ┌────────────────────┴─────────────────┐                 │
│           ▼  asyncio.gather()                    ▼                 │
│  ┌──────────────────┐                ┌───────────────────────┐     │
│  │    Agent 6       │                │       Agent 7         │     │ 
│  │    Interview     │                │    ATS Simulation     │     │
│  │  Adaptive Q&A    │                │  Workday · Greenhouse │     │
│  │  4D perf vector  │                │  Lever · Taleo        │     │
│  └──────────────────┘                └───────────────────────┘     │
│                                                                    │
│  [Canvas Output · Decision-State Export · Analyst Brief]           │
└────────────────────────────────────────────────────────────────────┘

Agent Breakdown

AgentRoleKey Mechanism1 · IngestionParse PDF/DOCX/text, extract sections, normalize schemaSection boundary detection: Education, Experience, Skills, Projects, Certifications2 · GenerationRAG-grounded bullet rewritesTop-5 FAISS retrieval mandatory before every LLM call; chunk IDs tagged to each output3 · QualityScore bullets 0.0–1.0; enforce threshold3-stage escalating constraint retry; unresolvable flag after all three stages fail4 · Weak DetectionIdentify resume weaknessesDetects vague_language, missing_metrics, employment_gap, skill_mismatch, overused_phrase5 · TailoringJD-specific optimizationSemantic alignment gate — hard abort + ranked section-level diagnostic if cosine < 0.66 · InterviewAdaptive Q&A generation4-dimensional performance vector (technical_depth, behavioral_clarity, communication_structure, domain_knowledge); recalibrates every 3 questions7 · ATS SimulationMulti-platform ATS scoringPer-platform reports for Workday, Greenhouse, Lever, Taleo: parse accuracy, keyword match rate, warnings


**⚡ Novel Inventive Steps
**
These five mechanisms form the core of the patent filing — no prior art identified for any of them.

1 · Live Profile Sync with JD-Filtered Approval Queue
GitHub and LinkedIn career deltas are fetched, embedded with SBERT, and filtered by cosine similarity ≥ 0.5 against the active job description before being surfaced to the user. Approved items are re-routed through the full RAG generation + Quality pipeline before canvas insertion. Staleness score: min(days_since_sync / 30, 1.0). No existing system implements this complete chain — staleness detection → JD-semantic filtering → human approval gate → quality-gated RAG re-generation.

2 · Semantic Alignment Gate with Hard Abort & Section Diagnosis
Before tailoring begins, the full resume embedding is compared to the JD embedding. If cosine similarity < 0.6, the Tailoring Agent hard-aborts and returns the three weakest resume sections by semantic distance — telling the user what to fix and why, not just that alignment is low. Jobscan and Rezi score alignment but never halt generation or surface section-level diagnostics.

3 · Three-Stage Escalating Constraint Retry
The Quality Agent applies progressively more constrained generation instructions derived from the specific failure mode of the preceding stage — not just resampling with the same prompt. Stage 3 constraint: one bullet, under 20 words, exactly one metric, past-tense action verb. Bullets failing all three stages are flagged status=unresolvable with a red warning badge and no accept/reject controls.

4 · Provenance-Linked Dispute Loop
Every scored output carries a structured Provenance object: agent name, FAISS chunk IDs, decision rationale, confidence (0.0–1.0). A WhyButton adjacent to every canvas bullet surfaces this provenance. Users can submit a dispute via POST /api/v1/canvas/dispute/{bullet_id} — the disagreement signal triggers Quality Agent re-evaluation with the dispute as additional context.

5 · Decision-State-Conditional Document Export
The exported DOCX/PDF is assembled exclusively from bullets with human-assigned accepted or user_modified status, in original section order. All pending or rejected content is excluded regardless of AI quality score. Every competing tool exports the full AI-generated output. This is the only system with per-bullet human decision gating at the export layer.


**🛠️ Tech Stack
**
LayerTechnologyFrontendReact 18 · TypeScript · Tailwind CSS · Canvas Resume EditorBackendFastAPI · Python 3.11 · Celery · RedisAI / MLSBERT all-MiniLM-L6-v2 · FAISS · LangChain · OpenAI / Groq LLaMA-3DatabasePostgreSQL · SQLAlchemyReal-timeWebSocket — per-agent AgentEvent broadcastInfrastructureDocker · Docker ComposeExportpython-docx · PDF pipelineVersion HistoryPython difflib · Canvas snapshot store


**📁 Project Structure
**

ResumeIntel/
├── backend/
│   ├── agents/
│   │   ├── ingestion_agent.py
│   │   ├── generation_agent.py
│   │   ├── quality_agent.py
│   │   ├── weak_detection_agent.py
│   │   ├── tailoring_agent.py
│   │   ├── interview_agent.py
│   │   └── ats_agent.py
│   ├── core/
│   │   ├── faiss_store.py
│   │   ├── sbert_embedder.py
│   │   └── pipeline.py
│   ├── api/
│   │   └── routes/
│   ├── tasks/
│   └── main.py
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── CanvasEditor/
│   │   │   ├── AgentProgressBar/
│   │   │   ├── ProfileSyncPanel/
│   │   │   └── InterviewPrep/
│   │   └── App.tsx
├── docs/
├── tests/
├── docker-compose.yml
└── Dockerfile


**🚀 Setup
**
Prerequisites


Python 3.11+, Node.js 18+, Docker & Docker Compose, PostgreSQL 15, Redis 7


bash# Clone
git clone https://github.com/anushkaanair/ResumeIntel.git
cd ResumeIntel

# Quickstart with Docker
docker-compose up --build

# --- Or run locally ---

# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Celery worker (separate terminal)
celery -A tasks worker --loglevel=info

# Frontend
cd frontend && npm install && npm run dev
Environment Variables
envDATABASE_URL=postgresql://user:password@localhost:5432/resumeintel
REDIS_URL=redis://localhost:6379
OPENAI_API_KEY=sk-...
SBERT_MODEL=all-MiniLM-L6-v2
QUALITY_THRESHOLD=0.7
ALIGNMENT_THRESHOLD=0.6




**📄 Patent Information
**

FieldDetailTitleAI-Powered Multi-Agent Resume Optimization and Career Intelligence SystemFiled underThe Patents Act, 1970 (39 of 1970) & The Patent Rules, 2003ApplicantsNeel Agarwal · Anushka Nair · Dr. Menaka S.InstitutionSRM Institute of Science and Technology, Tamil Nadu, IndiaTotal Claims13 (system, method, and application claims)Novel Inventive Steps5 — no prior art identified for anyStatusPending

**👤 Author
**
Anushka Nair — B.Tech CSE (AI & ML), SRM Institute of Science and Technology
Show Image
Show Image
Show Image

<div align="center">
<sub>Patent Pending under Indian Patent Law · © 2025 Anushka Nair & Neel Agarwal · SRM Institute of Science and Technology</sub>
</div>

