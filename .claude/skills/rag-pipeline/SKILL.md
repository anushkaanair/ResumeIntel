---
name: rag-pipeline
description: Implement RAG (Retrieval-Augmented Generation) patterns using SBERT embeddings and FAISS vector search. Use when working with embeddings, vector storage, retrieval logic, or grounding LLM outputs. Triggers on "embedding", "FAISS", "retrieval", "RAG", "vector search", "semantic search".
---

# RAG Pipeline Patterns

## Embedding
```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")  # 384-dim
embeddings = model.encode(segments, normalize_embeddings=True)
```

## FAISS Index
```python
import faiss
import numpy as np

dimension = 384
index = faiss.IndexIVFPQ(
    faiss.IndexFlatIP(dimension),  # Inner product (cosine after L2 norm)
    dimension, 100, 16, 8          # nlist=100, M=16, nbits=8
)
index.train(training_vectors)
index.add(vectors)
index.nprobe = 10
```

## Retrieval
```python
async def retrieve(self, query: str, top_k: int = 5) -> list[RetrievedSegment]:
    query_vector = self.embedder.encode([query], normalize_embeddings=True)
    scores, indices = self.index.search(query_vector, top_k)
    return [
        RetrievedSegment(content=self.segments[idx], score=float(score), segment_id=self.segment_ids[idx])
        for score, idx in zip(scores[0], indices[0])
        if idx != -1
    ]
```

## Critical Rules
- ALWAYS normalize embeddings before FAISS inner product search
- ALWAYS use retrieval before generation — no parametric-only outputs
- Index type IVF-PQ for production, IndexFlatIP for testing (<10K vectors)
- Per-user index isolation — never mix user data
