"""Application configuration and environment settings."""

import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load .env file from the backend root directory
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings(BaseModel):
    """Application settings loaded from environment variables."""

    PROJECT_NAME: str = "SafeRoom"
    API_V1_STR: str = "/api"
    ENVIRONMENT: str = Field(
        default_factory=lambda: os.getenv("ENVIRONMENT", "development")
    )
    DATABASE_URL: str = Field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://postgres:postgres@localhost:5432/saferoom",
        )
    )
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


settings = Settings()
