from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # LLM
    openai_api_key: str = ""

    # Database
    database_url: str = "postgresql://user:password@localhost:5432/resume_intel"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # FAISS
    faiss_index_dir: str = "./data/faiss_indices"

    # App
    app_env: str = "development"
    app_debug: bool = True
    app_port: int = 8000

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()
