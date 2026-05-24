from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import asyncpg

from app.config import settings

if TYPE_CHECKING:
    from fastapi import FastAPI


db_pool: asyncpg.Pool | None = None


@asynccontextmanager
async def lifespan_db(_app: FastAPI) -> AsyncIterator[None]:
    """FastAPI lifespan hook: open and close the asyncpg pool."""
    global db_pool
    db_pool = await asyncpg.create_pool(
        dsn=_normalize_dsn(settings.database_url),
        min_size=settings.db_pool_min_size,
        max_size=settings.db_pool_max_size,
    )
    try:
        yield
    finally:
        if db_pool is not None:
            await db_pool.close()
            db_pool = None


def _normalize_dsn(dsn: str) -> str:
    # asyncpg does not accept the SQLAlchemy +asyncpg suffix.
    return dsn.replace("postgresql+asyncpg://", "postgresql://")


async def get_connection() -> AsyncIterator[asyncpg.Connection]:
    """FastAPI dependency: acquire a pooled connection for the request."""
    if db_pool is None:
        raise RuntimeError("db_pool is not initialized — is lifespan_db registered?")
    async with db_pool.acquire() as conn:
        yield conn
