from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://talent_graph:talent_graph@localhost:5432/talent_graph"
    )

    # Neo4j
    neo4j_uri: str = Field(default="bolt://localhost:7687")
    neo4j_user: str = Field(default="neo4j")
    neo4j_password: str = Field(default="talent_graph")
    neo4j_database: str = Field(default="neo4j")

    # API
    api_key: str = Field(default="change-me-in-production")
    app_secret: str = Field(default="change-me-in-production")
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)

    # MLX LLM server
    llm_base_url: str = Field(default="http://localhost:8080/v1")
    llm_model: str = Field(default="mlx-community/Qwen3.5-35B-A3B-4bit")
    llm_timeout: int = Field(default=60)
    llm_semaphore_size: int = Field(default=1, ge=1)  # raise to 3 after latency measurement

    # Embeddings
    embedding_model: str = Field(default="BAAI/bge-small-en-v1.5")

    # Storage
    raw_data_dir: str = Field(default="data/raw")

    # External APIs
    openalex_email: str = Field(default="")
    github_token: str = Field(default="")

    # CORS (JSON array in env var, e.g., CORS_ORIGINS='["http://localhost:3000"]')
    cors_origins: list[str] = Field(default=["http://localhost:3000"])

    # Environment
    environment: str = Field(default="development")

    # Logging
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")  # "json" | "text"

    # Scheduler
    scheduler_openalex_query: str = Field(default="multimodal dialogue")
    scheduler_openalex_max_results: int = Field(default=200, ge=1, le=1000)
    scheduler_github_repos: list[str] = Field(default=["huggingface/transformers"])
    scheduler_interval_hours: int = Field(default=6, ge=1)
    scheduler_enabled: bool = Field(default=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
