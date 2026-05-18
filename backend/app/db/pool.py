"""
Database connection pool management.
"""

import asyncio
import logging
import asyncpg
from backend.app.config import settings

logger = logging.getLogger("smart_transit.db")

_pool: asyncpg.Pool | None = None


async def create_pool() -> asyncpg.Pool | None:
    """Create the asyncpg connection pool with retry logic."""
    global _pool
    retries = 10
    delay = 2

    for attempt in range(1, retries + 1):
        try:
            _pool = await asyncpg.create_pool(
                settings.DATABASE_URL,
                min_size=settings.DB_POOL_MIN_SIZE,
                max_size=settings.DB_POOL_MAX_SIZE,
            )
            logger.info("Database connection pool established.")
            return _pool
        except Exception as e:
            logger.warning("DB connection attempt %d/%d failed: %s", attempt, retries, e)
            if attempt < retries:
                await asyncio.sleep(delay)

    logger.error("Could not connect to database after %d retries. Running in degraded mode.", retries)
    return None


async def close_pool() -> None:
    """Close the connection pool gracefully."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("Database connection pool closed.")


def get_pool() -> asyncpg.Pool | None:
    """Return the current connection pool (may be None in degraded mode)."""
    return _pool
