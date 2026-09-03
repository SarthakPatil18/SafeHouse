"""Application configuration and environment settings."""

import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load .env file from the backend root directory
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


def _get_sanitized_database_url() -> str:
    """Sanitize and format database connection URL for async SQLAlchemy (asyncpg/aiosqlite)."""
    raw_url = os.getenv("DATABASE_URL", "").strip()

    # If DATABASE_URL is empty or was mistakenly set to an HTTPS web URL (e.g. Supabase REST URL)
    if not raw_url or raw_url.startswith("http://") or raw_url.startswith("https://"):
        return "sqlite+aiosqlite:///:memory:"

    # Convert standard postgres:// or postgresql:// to postgresql+asyncpg://
    if raw_url.startswith("postgres://"):
        return raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
    if raw_url.startswith("postgresql://") and not raw_url.startswith("postgresql+asyncpg://"):
        return raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    return raw_url


class Settings(BaseModel):
    """Application settings loaded from environment variables."""

    PROJECT_NAME: str = "SafeRoom"
    API_V1_STR: str = "/api"
    ENVIRONMENT: str = Field(
        default_factory=lambda: os.getenv("ENVIRONMENT", "development")
    )
    DATABASE_URL: str = Field(default_factory=_get_sanitized_database_url)
    SUPABASE_URL: str = Field(
        default_factory=lambda: os.getenv("SUPABASE_URL", "")
    )
    SUPABASE_KEY: str = Field(
        default_factory=lambda: os.getenv("SUPABASE_KEY", "")
    )
    GEMINI_API_KEY: str = Field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY", "")
    )
    DEVICE_TOKEN: str = Field(
        default_factory=lambda: os.getenv("DEVICE_TOKEN", "")
    )
    FRONTEND_ORIGIN: str = Field(
        default_factory=lambda: os.getenv("FRONTEND_ORIGIN", "http://localhost:5173,http://127.0.0.1:5173")
    )

    @property
    def cors_origins(self) -> list[str]:
        """Parsed list of allowed CORS origins."""
        return [o.strip() for o in self.FRONTEND_ORIGIN.split(",") if o.strip()]


settings = Settings()
