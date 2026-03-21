# RAG Engine Implementation

## Overview

The Retrieval-Augmented Generation (RAG) engine provides contextual grounding for the agent pipeline. When agents generate or tailor resume content, the RAG engine retrieves relevant segments from the user's own resume history to ensure factual accuracy and consistency. The engine uses SBERT for embedding and FAISS for fast vector search.

## Embedding Model

**Model:** `sentence-transformers/all-MiniLM-L6-v2`

| Property           | Value                |
|--------------------|----------------------|
| Embedding dimensions | 384                |
| Max sequence length | 256 tokens          |
| Model size          | ~80 MB              |
| Inference speed     | ~2ms per sentence (GPU), ~14ms (CPU) |
| Similarity metric   | Cosine similarity    |
| Training data       | 1B+ sentence pairs   |

**Why this model:**
- Strong balance between quality and speed for production use.
- 384 dimensions keeps memory footprint low while maintaining retrieval accuracy.
- Optimized for semantic similarity tasks, which aligns with matching resume content to job descriptions.
- Small enough to run on CPU in development, fast on GPU in production.

### Encoding Pipeline

```
Input text (segment or query)
        │
        ▼
┌─────────────────┐
│  Preprocessing   │
│  - Lowercase     │
│  - Strip excess  │
│    whitespace    │
│  - Truncate to   │
│    256 tokens    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  SBERT Encoder   │──── all-MiniLM-L6-v2
│  (batch encode)  │──── Batch size: 32
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  L2 Normalize    │──── Unit vectors for cosine similarity
└────────┬────────┘
         │
         ▼
    384-dim vector
```

## FAISS Index Configuration

**Index type:** `IVF-PQ` (Inverted File with Product Quantization)

| Parameter     | Value   | Description                                    |
|---------------|---------|------------------------------------------------|
| `nlist`       | 100     | Number of Voronoi cells (inverted lists)       |
| `M`           | 16      | Number of sub-quantizers for PQ                |
| `nbits`       | 8       | Bits per sub-quantizer (256 centroids each)    |
| `nprobe`      | 10      | Number of cells to search at query time        |
| `metric`      | L2      | Distance metric (on normalized vectors = cosine)|

### Index Build Process

```
Segment embeddings (N x 384)
        │
        ▼
┌─────────────────┐
│  Train IVF       │──── Requires min(N, nlist * 39) training vectors
│  (k-means on     │──── Clusters vectors into 100 Voronoi cells
│   100 centroids) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Train PQ        │──── Learns 16 sub-quantizers, 8 bits each
│  (product        │──── Compresses 384-d vector to 16 bytes
│   quantization)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Add vectors     │──── Insert all segment vectors into trained index
│  with IDs        │──── Map FAISS IDs to segment UUIDs
└────────┬────────┘
         │
         ▼
   Trained IVF-PQ index (.index file)
```

### Memory and Storage Estimates

| Segments per user | Raw vector size | PQ compressed size | Index file size |
|-------------------|-----------------|--------------------|-----------------|
| 50                | 75 KB           | ~1 KB              | ~15 KB          |
| 200               | 300 KB          | ~4 KB              | ~50 KB          |
| 1,000             | 1.5 MB          | ~16 KB             | ~200 KB         |

PQ compression achieves roughly 24x compression (384 floats = 1536 bytes down to 16 bytes per vector).

## Segmentation Strategy

Resume text is segmented at the section level, with further subdivision for long sections:

### Segmentation Rules

1. **Section-level split:** The IngestionAgent identifies sections (experience, education, skills, projects, summary, certifications). Each section becomes a primary segment.

2. **Bullet-level split for experience/projects:** Within experience and project sections, each individual bullet point (or group of 2-3 related bullets) becomes a separate segment. This gives fine-grained retrieval.

3. **Chunk size target:** Each segment targets 50-150 tokens. Segments shorter than 20 tokens are merged with an adjacent segment. Segments longer than 200 tokens are split at sentence boundaries.

4. **Overlap:** No overlap between segments from different sections. Within a section, a 1-sentence overlap is added between consecutive chunks to preserve context at boundaries.

### Segment Metadata

Each segment carries metadata stored alongside its vector:

```python
class SegmentMetadata:
    segment_id: str          # UUID
    resume_id: str           # Parent resume UUID
    user_id: str             # Owner
    section_type: str        # experience, education, skills, etc.
    position: int            # Order in original document
    content: str             # Original text (for retrieval display)
    created_at: datetime     # Timestamp
```

## Retrieval Flow

### Query-Time Retrieval

```
Query text (JD excerpt or optimization prompt)
        │
        ▼
┌─────────────────┐
│  Encode query    │──── SBERT → 384-d normalized vector
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Load user index │──── FAISS index from disk: /data/faiss/{user_id}.index
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  FAISS search    │──── Search nprobe=10 cells
│  top-k=20        │──── Return 20 nearest neighbors
└────────┬────────┘
         │  (IDs, distances)
         ▼
┌─────────────────┐
│  ID mapping      │──── Map FAISS integer IDs → segment UUIDs
│                  │──── Fetch full segment metadata from PostgreSQL
└────────┬────────┘
         │  ranked segments with content
         ▼
┌─────────────────┐
│  Score filter    │──── Discard results with distance > threshold (0.8)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Context Builder │──── Select top segments within token budget
│  (max 2048 tok)  │──── Deduplicate overlapping content
│                  │──── Order by relevance score
└────────┬────────┘
         │
         ▼
   Context string for LLM prompt
```

### Retrieval Parameters

| Parameter              | Value   | Description                             |
|------------------------|---------|-----------------------------------------|
| Top-k (initial)       | 20      | Candidates from FAISS                    |
| Distance threshold     | 0.8     | Max L2 distance to accept (lower = more similar) |
| Final context segments | 5-10    | After filtering and dedup               |
| Token budget           | 2048    | Max tokens in assembled context          |
| nprobe                 | 10      | FAISS cells to probe                     |

## Per-User Index Isolation

Each user has their own FAISS index file, ensuring complete data isolation:

### Storage Layout

```
/data/faiss/
├── {user_id_1}.index        # FAISS index binary
├── {user_id_1}.meta.json    # ID mapping + metadata
├── {user_id_2}.index
├── {user_id_2}.meta.json
└── ...
```

### Index Lifecycle

1. **Creation:** When a user uploads their first resume, a new FAISS index is created and trained on their segments.

2. **Updates:** When a new resume is uploaded, new segment vectors are added to the existing index. If the index structure degrades (too many additions without retraining), the index is rebuilt.

3. **Rebuild trigger:** Rebuild when total vectors exceed 2x the count at last training time.

4. **Deletion:** When a user deletes their account, the index file and metadata are removed from disk.

### Concurrency

- Reads are lock-free (FAISS supports concurrent reads).
- Writes acquire a per-user mutex to prevent concurrent modifications.
- Index loading uses an LRU cache (max 100 users in memory) to avoid repeated disk reads.

```python
class IndexManager:
    _cache: LRUCache[str, faiss.Index]  # user_id → loaded index
    _locks: dict[str, asyncio.Lock]      # per-user write locks

    async def search(self, user_id: str, query_vec: np.ndarray, k: int = 20):
        index = await self._load_or_cache(user_id)
        distances, ids = index.search(query_vec, k)
        return distances, ids

    async def add_vectors(self, user_id: str, vectors: np.ndarray, ids: list[int]):
        async with self._locks[user_id]:
            index = await self._load_or_cache(user_id)
            index.add_with_ids(vectors, ids)
            faiss.write_index(index, self._path(user_id))
```

## Fallback Behavior

- If a user's index has fewer than 40 vectors (minimum for IVF training with nlist=100), the system falls back to a flat `IndexFlatIP` (exact brute-force search). This is acceptable for small vector counts.
- If the SBERT model fails to load, the system returns an error and does not proceed with generation (no silent fallback to random retrieval).
- If FAISS search returns zero results above the distance threshold, the agent pipeline proceeds without RAG context and logs a warning.
