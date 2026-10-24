from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # LLM
    openai_api_key: str = ""
    llm_provider: str = "openai"  # "openai" or "ollama"
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "llama3"
    openai_model: str = "gpt-4o"
    # Any OpenAI-compatible endpoint (Groq, Together, Gemini's compat API, ...)
    openai_base_url: str = ""

    # Database
    database_url: str = "postgresql://user:password@localhost:5432/resume_intel"

    # Redis — used for job result storage and WebSocket pub/sub
    redis_url: str = "redis://localhost:6379/0"
    redis_ttl_seconds: int = 3600  # how long to keep pipeline results

    # FAISS
    faiss_index_dir: str = "./data/faiss_indices"

    # Alignment gate (cosine between resume and JD embeddings). 0.33 was
    # calibrated on 12 real target postings (min 0.38) and 8 unrelated ones
    # (max 0.38): it blocks clearly unrelated roles without rejecting real ones.
    # The earlier 0.60 sat above every real posting. Re-calibrate with
    # the same procedure (see README, "Alignment gate") if you change the embedding model.
    alignment_threshold: float = 0.33

    # Access control for a personal deployment. Empty = open (local dev only).
    api_secret_key: str = ""
    # Comma-separated browser origins allowed to call the API.
    # Built frontend served by the API itself (set by run_private.sh).
    frontend_dist: str = "./frontend/dist"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # App
    app_env: str = "development"
    app_debug: bool = True
    app_port: int = 8000

    # LinkedIn OAuth (for live profile sync)
    linkedin_client_id: str = ""
    linkedin_client_secret: str = ""
    linkedin_redirect_uri: str = "http://localhost:8000/api/v1/auth/linkedin/callback"
    frontend_base_url: str = "http://localhost:5173"

    # GitHub OAuth (for live profile sync — 3-legged per-user flow)
    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = "http://localhost:8000/api/v1/auth/github/callback"
    # Legacy server-side token (fallback only if OAuth not configured)
    github_access_token: str = ""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()
