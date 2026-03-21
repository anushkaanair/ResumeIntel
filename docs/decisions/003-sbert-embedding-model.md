# ADR-003: all-MiniLM-L6-v2 as the Embedding Model

**Date:** 2026-03-21

**Status:** Accepted

## Context

The RAG engine needs an embedding model to convert resume segments and job description queries into dense vectors for similarity search. The model must balance quality, speed, and resource consumption. Models evaluated:

1. **all-MiniLM-L6-v2** (SBERT, 384 dimensions, ~80MB) -- A compact, well-benchmarked sentence transformer optimized for semantic similarity.
2. **all-mpnet-base-v2** (SBERT, 768 dimensions, ~420MB) -- A larger model with higher benchmark scores but significantly more memory and compute requirements.
3. **OpenAI text-embedding-ada-002** (1536 dimensions, API-based) -- High quality embeddings via API call, but introduces external dependency, latency, and per-token cost.
4. **E5-large-v2** (1024 dimensions, ~1.3GB) -- State-of-the-art retrieval model but very large.

Key considerations:

- **Use case:** Matching resume segments to job description queries. This is a semantic similarity task, not a general-purpose retrieval task over millions of documents.
- **Latency budget:** Embedding happens at upload time (batch, can be slower) and at query time (must be fast, under 50ms).
- **Infrastructure:** The application runs on modest hardware (4-8 CPU cores, 16GB RAM, optional GPU). The model must fit comfortably alongside the web server, database, and FAISS.
- **Vector storage:** Larger dimensions mean larger FAISS indexes, more memory, and slower search. With IVF-PQ compression, larger vectors still require more sub-quantizers.

## Decision

We will use `sentence-transformers/all-MiniLM-L6-v2` as the embedding model, producing 384-dimensional vectors.

## Consequences

### Better

- **Small footprint:** ~80MB model size fits easily in memory alongside other application components. No GPU required for acceptable performance.
- **Fast inference:** ~14ms per sentence on CPU, ~2ms on GPU. Batch encoding of an entire resume (20-50 segments) completes in under 1 second on CPU.
- **Low-dimensional vectors (384-d):** Smaller FAISS indexes, faster search, less memory consumption. IVF-PQ with M=16 sub-quantizers compresses each vector to just 16 bytes.
- **Well-benchmarked:** Consistently ranks in the top tier for semantic textual similarity tasks on the MTEB benchmark, despite being one of the smallest models.
- **No external API dependency:** Runs locally, so no per-token cost, no API rate limits, no network latency, and no data leaving the server.
- **Broad ecosystem support:** Widely used in the sentence-transformers ecosystem with extensive documentation, community support, and known behavior.

### Worse

- **Lower ceiling on retrieval quality:** all-mpnet-base-v2 and E5-large-v2 score higher on retrieval benchmarks. For very nuanced semantic distinctions (e.g., distinguishing between "led a team" and "managed a department"), the smaller model may produce closer embeddings than desired.
- **256 token limit:** Maximum input sequence is 256 tokens. Resume segments longer than this are truncated, potentially losing tail information. Larger models support 512 tokens.
- **English-centric:** Performance degrades on non-English resumes. The model was primarily trained on English text. Multilingual support would require a different model (e.g., paraphrase-multilingual-MiniLM-L12-v2).

### Mitigated

- **Retrieval quality** is mitigated by the segmentation strategy: resume sections are split into small, focused chunks (50-150 tokens) that are well within the model's sweet spot. For the specific domain of resume-to-JD matching, the quality difference between MiniLM-L6-v2 and larger models is marginal based on our internal evaluation.
- **Token limit** is mitigated by the chunking strategy that keeps segments under 150 tokens. The 256-token limit is rarely hit in practice.
- **English-only limitation** is acceptable for the initial product scope, which targets English-language resumes. Multilingual support is tracked as a future enhancement, and swapping the embedding model is straightforward since the FAISS indexes are per-user and can be rebuilt on model change.
