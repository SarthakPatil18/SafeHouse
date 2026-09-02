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

# Create async engine with pooled connections
engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
)

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

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
