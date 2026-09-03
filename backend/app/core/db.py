"""Database connection, async engine, session factory, and bootstrap helper."""

import asyncio
from collections.abc import AsyncGenerator
from typing import Optional
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.exc import (
    DBAPIError,
    DisconnectionError,
    InterfaceError,
    OperationalError,
    PendingRollbackError,
    TimeoutError as SATimeoutError,
)
from sqlalchemy import text
from app.core.config import settings
from app.core.logging import logger
from app.models.base import Base

_is_fallback_engine: bool = False

DB_CONNECTION_EXCEPTIONS = (
    OperationalError,
    InterfaceError,
    DisconnectionError,
    SATimeoutError,
    PendingRollbackError,
    ConnectionRefusedError,
    ConnectionResetError,
    OSError,
    asyncio.TimeoutError,
)


def is_db_connection_error(exc: Exception) -> bool:
    """Check if exception represents a genuine database connection, disconnection, or network failure."""
    if isinstance(exc, DB_CONNECTION_EXCEPTIONS):
        return True
    if isinstance(exc, DBAPIError) and exc.connection_invalidated:
        return True
    err_str = str(exc).lower()
    if any(k in err_str for k in [
        "connection refused",
        "connection reset",
        "cannot connect to host",
        "connection closed",
        "is the server running",
        "nodename nor servname provided",
        "timeout expired",
        "connect call failed",
        "could not connect",
        "no route to host",
    ]):
        return True
    return False


def _init_engine() -> AsyncEngine:
    """Initialize primary async database engine with graceful fallback and Supabase pooler support."""
    global _is_fallback_engine
    db_url = settings.DATABASE_URL
    connect_args = {}

    if "sqlite" in db_url and ":memory:" in db_url:
        _is_fallback_engine = True

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
        _is_fallback_engine = True
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
    """Verify whether database connection is active and responsive.

    Returns False if operating in fallback in-memory mode or if ping fails.
    """
    if _is_fallback_engine:
        return False
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
        logger.warning("Database session unavailable (%s), operating in memory fallback.", e)
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

            # Auto-bootstrap default rover device so foreign keys never fail
            try:
                await conn.execute(
                    text("""
                        INSERT INTO devices (id, name, device_type, status, battery_level, created_at)
                        VALUES ('rover_01', 'SafeRoom Rover 01', 'rover', 'IDLE', 98.0, CURRENT_TIMESTAMP)
                        ON CONFLICT (id) DO NOTHING;
                    """)
                )
                await conn.execute(
                    text("""
                        INSERT INTO rooms (id, name, type, x, y, order_index, enabled, created_at)
                        VALUES 
                            ('room_1', 'Living Room', 'living_room', 2.0, 3.0, 1, true, CURRENT_TIMESTAMP),
                            ('room_2', 'Master Bedroom', 'bedroom', 6.0, 3.0, 2, true, CURRENT_TIMESTAMP),
                            ('room_3', 'Guest Bedroom', 'bedroom', 6.0, 7.0, 3, true, CURRENT_TIMESTAMP),
                            ('room_4', 'Kitchen', 'kitchen', 2.0, 7.0, 4, true, CURRENT_TIMESTAMP)
                        ON CONFLICT (id) DO NOTHING;
                    """)
                )
                await conn.execute(
                    text("""
                        INSERT INTO room_baselines (id, room_id, gas_mq135_max, gas_mq2_max, motion_mode, no_motion_timeout_seconds, updated_at)
                        VALUES
                            ('bl_room_1', 'room_1', 100.0, 100.0, 'expect_presence', 3600, CURRENT_TIMESTAMP),
                            ('bl_room_2', 'room_2', 80.0, 80.0, 'expect_presence', 28800, CURRENT_TIMESTAMP),
                            ('bl_room_3', 'room_3', 80.0, 80.0, 'expect_absence', null, CURRENT_TIMESTAMP),
                            ('bl_room_4', 'room_4', 120.0, 150.0, 'ignore', null, CURRENT_TIMESTAMP)
                        ON CONFLICT (id) DO NOTHING;
                    """)
                )
            except Exception as e:
                logger.debug("Database default rows bootstrap note: %s", e)
    except Exception as e:
        logger.warning("Database schema bootstrap note: %s", e)
