"""Database connection, async engine, session factory, and bootstrap helper."""

from collections.abc import AsyncGenerator
from typing import Optional
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from sqlalchemy import text
from app.core.config import settings
from app.core.logging import logger
from app.models.base import Base


def _init_engine() -> AsyncEngine:
    """Initialize primary async database engine with graceful fallback and Supabase pooler support."""
    db_url = settings.DATABASE_URL
    connect_args = {}

    # Supabase Transaction Pooler (port 6543 / PgBouncer) requires disabling prepared statement cache in asyncpg
    if "asyncpg" in db_url:
        connect_args["statement_cache_size"] = 0
        connect_args["prepared_statement_cache_size"] = 0

    try:
        return create_async_engine(
            db_url,
            echo=False,
            future=True,
            connect_args=connect_args,
        )
    except Exception as e:
        logger.warning(
            "Primary database engine init failed for (%s): %s. Initializing in-memory fallback.",
            db_url,
            e,
        )
        return create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            echo=False,
            future=True,
        )


# Create async engine with pooled connections
engine: AsyncEngine = _init_engine()

# Async session factory
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def check_db_health() -> bool:
    """Verify whether database connection is active and responsive."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            return True
    except Exception:
        return False


async def get_db() -> AsyncGenerator[Optional[AsyncSession], None]:
    """FastAPI dependency for yielding transactional database sessions with fallback."""
    session = None
    try:
        session = async_session_factory()
    except Exception as e:
        logger.debug("Database session unavailable (%s), operating in memory fallback.", e)
        yield None
        return

    async with session:
        try:
            yield session
        except Exception:
            try:
                await session.rollback()
            except Exception:
                pass
            raise


async def init_db() -> None:
    """Bootstrap all database tables using metadata.create_all (Alembic-free)."""
    # Import all models to ensure they are registered on Base.metadata
    import app.models  # noqa: F401

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            try:
                await conn.execute(
                    text("ALTER TABLE sensor_readings ADD COLUMN IF NOT EXISTS source VARCHAR DEFAULT 'live';")
                )
            except Exception as e:
                logger.debug("Database column migration note: %s", e)
    except Exception as e:
        logger.warning("Database schema bootstrap note: %s", e)
