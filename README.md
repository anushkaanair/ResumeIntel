# Resume Intel

AI-powered resume optimization platform built with a multi-agent architecture. Upload a resume and a target job description, and the system analyzes, scores, and suggests improvements using coordinated AI agents backed by RAG retrieval.

## Tech Stack

- **Backend:** Python 3.11, FastAPI, Celery, SQLAlchemy, Alembic
- **AI/ML:** OpenAI API, Sentence Transformers, FAISS
- **Frontend:** React, TypeScript, Vite, Tailwind CSS
- **Infrastructure:** PostgreSQL, Redis, Docker

## Setup

```bash
# Clone the repository
git clone <repo-url>
cd resume-intel

# Copy environment file and fill in your keys
cp .env.example .env

# Start infrastructure services
docker compose up -d postgres redis

# Install Python dependencies
pip install -e ".[dev]"

# Run database migrations
alembic upgrade head

# Start the backend server
uvicorn src.main:app --reload --port 8000

# In a separate terminal, start the frontend
cd frontend
npm install
npm run dev
```

## Project Structure

```
resume-intel/
├── src/                  # Backend source code
│   ├── config/           # Settings and configuration
│   ├── agents/           # AI agent implementations
│   ├── rag/              # Retrieval-augmented generation
│   ├── models/           # SQLAlchemy models
│   ├── api/              # FastAPI routers
│   └── exceptions.py     # Custom exception hierarchy
├── frontend/             # React/TypeScript frontend
├── tests/                # Test suite
├── docker-compose.yml    # Container orchestration
├── Dockerfile            # Backend container image
└── pyproject.toml        # Python project config
```

## Team

- **Neel** -- AI/Backend architecture and agent system
- **Teammate** -- Frontend development and UI/UX
