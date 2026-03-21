# ADR-002: FAISS Over Pinecone for Vector Storage

**Date:** 2026-03-21

**Status:** Accepted

## Context

The RAG engine requires a vector store to index resume segments and perform similarity search against job descriptions. The two primary candidates evaluated were:

1. **Pinecone:** A fully managed cloud vector database with built-in scaling, filtering, and a hosted API.
2. **FAISS (Facebook AI Similarity Search):** An open-source library for efficient similarity search, running locally or on self-managed infrastructure.

Key factors in the decision:

- **Data volume:** Each user has 50-200 resume segments. Total expected user base for the initial launch is under 10,000 users. This means roughly 500K-2M total vectors, well within a single-machine FAISS deployment.
- **Privacy:** Resume data is sensitive. Users may not want their career history stored in a third-party cloud vector database.
- **Cost:** Pinecone charges based on vector count and query volume. At scale, this becomes a significant recurring cost. FAISS has zero licensing cost.
- **Latency:** FAISS runs in-process, returning results in under 1ms for the expected index sizes. Pinecone adds network round-trip latency (10-50ms per query).
- **Per-user isolation:** The system requires strict per-user data isolation. FAISS supports this naturally through separate index files. Pinecone would require namespace management or metadata filtering.

## Decision

We will use FAISS with IVF-PQ indexing for vector storage, with per-user index files stored on disk and loaded into an LRU cache at query time.

## Consequences

### Better

- **Zero external dependency cost:** No per-vector or per-query billing. Infrastructure cost is limited to disk storage and memory on the application server.
- **In-process speed:** Sub-millisecond search latency for per-user indexes of 50-200 vectors. No network overhead.
- **Data sovereignty:** All vector data stays on our infrastructure. No resume content is sent to a third-party vector database service.
- **Per-user isolation by design:** Each user gets their own `.index` file. There is no risk of cross-user data leakage through metadata filtering bugs.
- **Offline development:** Developers can run the full stack locally without needing Pinecone API keys or internet access.
- **Predictable performance:** No dependency on a third-party service's availability, rate limits, or latency spikes.

### Worse

- **Operational burden:** We are responsible for index file management, backups, and recovery. Pinecone handles all of this automatically.
- **No built-in metadata filtering:** FAISS does not support filtering by metadata fields during search. Post-search filtering must be done in application code.
- **Scaling ceiling:** If the system grows to millions of users, per-user index files become unwieldy. A centralized index with namespace partitioning would be needed, requiring architectural changes.
- **No managed monitoring:** Pinecone provides dashboards for query latency, index health, and usage. With FAISS, we must build our own monitoring.
- **Index training complexity:** IVF-PQ indexes require a training step. For users with very few vectors (fewer than 40), we must fall back to brute-force flat indexes.

### Mitigated

- **Operational burden** is mitigated by keeping index files small (per-user, under 200KB each) and including index files in the standard backup pipeline alongside PostgreSQL.
- **Metadata filtering** is mitigated by storing segment metadata in PostgreSQL and performing joins after FAISS returns candidate IDs. For the expected query patterns (retrieve top-k for one user), this adds negligible overhead.
- **Scaling ceiling** is mitigated by the per-user architecture: even at 100K users, total disk usage for indexes is under 20GB. A migration to a centralized solution would only be needed at much larger scale and can be planned as a future evolution.
- **Index training** for small vector sets is mitigated by a fallback to `IndexFlatIP` (exact search) when a user has fewer than 40 vectors, which is fast enough for small collections.
