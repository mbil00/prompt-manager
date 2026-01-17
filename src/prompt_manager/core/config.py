"""Application configuration using pydantic-settings."""

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="PM_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API Server
    api_key: str = "dev-secret-key"
    database_url: str = "sqlite+aiosqlite:///./prompts.db"
    host: str = "0.0.0.0"
    port: int = 8000
    allow_localhost_bypass: bool = True

    # CLI
    api_url: str = "http://localhost:8000"
    default_format: Literal["plain", "json", "yaml", "table"] = "plain"
    editor: str = "vim"

    # Paths
    config_dir: Path = Path.home() / ".config" / "prompt-manager"

    @property
    def sync_database_url(self) -> str:
        """Get synchronous database URL for Alembic migrations."""
        return self.database_url.replace("+aiosqlite", "")


settings = Settings()
