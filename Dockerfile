# ---------- build ----------
FROM python:3.11-slim AS builder
WORKDIR /app
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1

# CPU-only torch keeps the image ~2 GB smaller than the default CUDA wheels.
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch

COPY pyproject.toml ./
COPY src ./src
RUN pip install .

# Bake the embedding model into the image so the first request does not download it.
ENV HF_HOME=/opt/hf
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# ---------- runtime ----------
FROM python:3.11-slim
WORKDIR /app
RUN addgroup --system app && adduser --system --ingroup app app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /opt/hf /opt/hf
COPY src ./src
ENV HF_HOME=/opt/hf HF_HUB_OFFLINE=1 PYTHONUNBUFFERED=1 APP_ENV=production
RUN mkdir -p /app/data/faiss_indices && chown -R app:app /app
USER app
EXPOSE 8000
# Railway/Render inject $PORT; default to 8000 elsewhere.
CMD ["sh", "-c", "uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
