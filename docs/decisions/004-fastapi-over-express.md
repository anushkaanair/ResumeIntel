# ADR-004: FastAPI Over Express.js for the API Layer

**Date:** 2026-03-21

**Status:** Accepted

## Context

The API layer needs a web framework to handle HTTP requests, validate inputs, manage authentication, and dispatch background tasks to the agent pipeline. The two candidates were:

1. **FastAPI (Python):** An async Python web framework with built-in Pydantic validation, automatic OpenAPI docs, and native async/await support.
2. **Express.js (Node.js):** The most widely used Node.js web framework, with a large middleware ecosystem and JavaScript/TypeScript support.

Key factors:

- **ML ecosystem:** The intelligence layer (SBERT, FAISS, LLM client libraries) is entirely Python-based. The agent pipeline, RAG engine, and all ML utilities are written in Python.
- **Team skills:** The development team has stronger Python experience than Node.js/TypeScript.
- **Type safety:** The API handles complex nested request/response structures (optimization results, agent outputs). Strong input validation is critical.
- **Async requirements:** Optimization pipelines run as background tasks. The API must handle concurrent requests efficiently while dispatching long-running work.
- **Documentation:** The API will be consumed by the React frontend and potentially by external integrations. Auto-generated API documentation is highly valuable.

## Decision

We will use FastAPI (Python 3.11+) as the API framework, with Pydantic v2 for request/response validation and Celery + Redis for background task execution.

## Consequences

### Better

- **Single language stack (Python):** The entire backend -- API layer, agent pipeline, RAG engine, ML utilities -- is in Python. No cross-language serialization, no separate runtime environments, no language boundary debugging.
- **Native Pydantic validation:** Request and response models are defined as Pydantic classes. Input validation, serialization, and documentation are handled automatically. The same Pydantic models used for inter-agent contracts can be reused as API schemas.
- **Automatic OpenAPI/Swagger docs:** FastAPI generates interactive API documentation at `/docs` (Swagger UI) and `/redoc` (ReDoc) from the Pydantic models with zero manual effort.
- **Async-first:** FastAPI is built on Starlette and supports native `async def` endpoints. This pairs well with the async agent pipeline and non-blocking I/O to PostgreSQL and Redis.
- **Dependency injection:** FastAPI's `Depends()` system cleanly handles cross-cutting concerns like authentication, rate limiting, and database sessions without middleware complexity.
- **Direct ML library access:** SBERT, FAISS, NumPy, and LLM client libraries are Python-native. No need for inter-process communication, gRPC bridges, or subprocess calls.

### Worse

- **Lower raw throughput:** Python's per-request overhead is higher than Node.js for I/O-bound workloads. Express.js can handle more concurrent lightweight requests on the same hardware.
- **GIL limitations:** Python's Global Interpreter Lock limits true CPU parallelism within a single process. CPU-heavy operations (embedding computation) block the event loop unless offloaded to a thread pool or separate process.
- **Smaller middleware ecosystem:** Express.js has a larger ecosystem of middleware for common tasks (CORS, rate limiting, logging). FastAPI's ecosystem is growing but not as extensive.
- **Frontend/backend language mismatch:** The React frontend uses TypeScript. Shared types between frontend and backend require code generation (e.g., from OpenAPI spec) rather than direct type sharing.

### Mitigated

- **Throughput** is not a practical concern for this application. The heaviest operation (optimization pipeline) runs as a background Celery task, not in the request-response cycle. API endpoints are lightweight dispatchers and data fetchers where FastAPI's performance is more than adequate.
- **GIL limitations** are mitigated by offloading CPU-intensive work (SBERT encoding, FAISS search) to Celery workers running in separate processes. The FastAPI process handles only I/O-bound request routing.
- **Middleware gaps** are mitigated by well-maintained FastAPI-compatible libraries: `slowapi` for rate limiting, `fastapi-cors` for CORS, and `python-jose` for JWT handling.
- **Frontend type mismatch** is mitigated by generating TypeScript types from the OpenAPI specification using `openapi-typescript-codegen`. This keeps frontend and backend types synchronized automatically as part of the CI pipeline.
