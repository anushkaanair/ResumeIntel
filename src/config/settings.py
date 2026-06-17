from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # LLM
    openai_api_key: str = ""
    llm_provider: str = "openai"  # "openai" or "ollama"
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "llama3"
    openai_model: str = "gpt-4o"

    # Database
    database_url: str = "postgresql://user:password@localhost:5432/resume_intel"

    # Redis — used for job result storage and WebSocket pub/sub
    redis_url: str = "redis://localhost:6379/0"
    redis_ttl_seconds: int = 3600  # how long to keep pipeline results

    # FAISS
    faiss_index_dir: str = "./data/faiss_indices"

    # App
    app_env: str = "development"
    app_debug: bool = True
    app_port: int = 8000

    # LinkedIn OAuth (for live profile sync)
    linkedin_client_id: str = ""
    linkedin_client_secret: str = ""
    linkedin_redirect_uri: str = "http://localhost:8000/api/v1/auth/linkedin/callback"
    frontend_base_url: str = "http://localhost:5173"

    # GitHub OAuth (for live profile sync)
    github_client_id: str = ""
    github_client_secret: str = ""
    # Personal access token for server-side GitHub API calls (no user OAuth needed)
    github_access_token: str = ""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()
