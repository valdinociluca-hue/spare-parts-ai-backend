from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")
os.environ.setdefault("JWT_SECRET", "test-secret")


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    from app.main import app  # imported here so env vars are set first

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
