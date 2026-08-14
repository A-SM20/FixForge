"""Application configuration via pydantic-settings.

Loads settings from environment variables or a .env file.
Why pydantic-settings: type-safe, validates on startup (fail fast),
and provides a single source of truth for all configuration.
"""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/fixforge"

    @field_validator("database_url", mode="before")
    @classmethod
    def assemble_async_db_url(cls, v: str) -> str:
        """Convert standard postgres:// or postgresql:// to postgresql+asyncpg://."""
        if isinstance(v, str):
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+asyncpg://", 1)
            elif v.startswith("postgresql://") and not v.startswith("postgresql+asyncpg://"):
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    # LLM
    openai_api_key: str = "sk-placeholder"
    openai_model: str = "gpt-4o"

    # GitHub
    github_token: str = "ghp-placeholder"

    # Agent
    max_iterations: int = 5

    # Sandbox (Docker)
    sandbox_mem_limit: str = "1g"
    sandbox_cpu_limit: int = 1_000_000_000  # 1 CPU in nanocpus
    sandbox_timeout: int = 300  # seconds

    # Server
    debug: bool = False
    cors_origins: list[str] = ["*"]  # Allow all origins for cloud deployment


def get_settings() -> Settings:
    """Factory function for settings; enables easy override in tests."""
    return Settings()
