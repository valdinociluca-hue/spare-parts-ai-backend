"""
app/db/session.py — Async database engine and session factory.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config.settings import settings

engine = create_async_engine(
    settings.database_url,
    echo          = False,
    pool_size     = 5,
    max_overflow  = 10,
    pool_pre_ping = True,
)

AsyncSessionLocal = async_sessionmaker(
    bind             = engine,
    class_           = AsyncSession,
    expire_on_commit = False,
    autoflush        = False,
    autocommit       = False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — one session per request."""
    async with AsyncSessionLocal() as session:
        yield session


async def create_tables() -> None:
    """Create all tables on startup. Use Alembic for production migrations."""
    from app.db.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
