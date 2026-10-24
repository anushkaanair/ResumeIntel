# Hugging Face Spaces (free CPU Space, 16 GB RAM). Redis runs inside the container,
# so there is nothing else to provision. State is lost when the Space restarts.
FROM python:3.11-slim AS builder
WORKDIR /app
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch
COPY pyproject.toml ./
COPY src ./src
RUN pip install .
ENV HF_HOME=/opt/hf
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends redis-server && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /opt/hf /opt/hf
COPY src ./src
COPY start.sh ./start.sh
ENV HF_HOME=/opt/hf HF_HUB_OFFLINE=1 PYTHONUNBUFFERED=1 APP_ENV=production \
    REDIS_URL=redis://127.0.0.1:6379/0 FAISS_INDEX_DIR=/tmp/faiss REDIS_TTL_SECONDS=86400
RUN chmod +x start.sh && mkdir -p /tmp/faiss && chown -R app /app /tmp/faiss
USER app
EXPOSE 7860
CMD ["./start.sh"]
