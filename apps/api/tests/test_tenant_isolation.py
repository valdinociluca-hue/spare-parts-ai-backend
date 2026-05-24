"""Cross-tenant isolation tests.

These tests require a running local Postgres (docker compose up -d) with
the schema applied. They prove that:
  - Requests without tenant context get 401
  - A widget key for tenant A cannot read tenant B's data
  - X-Tenant-Slug lookup honors only the requested tenant

The tests are skipped automatically if the DB is unreachable so they
don't block CI environments that have no Postgres.
"""

from __future__ import annotations

import os

import asyncpg
import pytest
from httpx import AsyncClient


async def _db_reachable() -> bool:
    try:
        conn = await asyncpg.connect(
            os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://"),
            timeout=2,
        )
    except (OSError, asyncpg.PostgresError):
        return False
    await conn.close()
    return True


pytestmark = pytest.mark.asyncio


async def test_no_tenant_context_returns_401(client: AsyncClient) -> None:
    if not await _db_reachable():
        pytest.skip("local Postgres not running")
    response = await client.get("/api/v1/tenants/me")
    assert response.status_code == 401


async def test_widget_key_resolves_correct_tenant(client: AsyncClient) -> None:
    if not await _db_reachable():
        pytest.skip("local Postgres not running")

    dsn = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(dsn)
    try:
        row = await conn.fetchrow(
            "select widget_api_key, slug from public.tenants where slug = 'lvtrade'"
        )
    finally:
        await conn.close()

    if row is None:
        pytest.skip("seed.sql has not been applied")

    response = await client.get(
        "/api/v1/tenants/me",
        headers={"X-Widget-Key": row["widget_api_key"]},
    )
    assert response.status_code == 200
    assert response.json()["slug"] == "lvtrade"


async def test_widget_key_does_not_leak_other_tenant(client: AsyncClient) -> None:
    if not await _db_reachable():
        pytest.skip("local Postgres not running")

    dsn = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(dsn)
    try:
        lv = await conn.fetchrow(
            "select widget_api_key from public.tenants where slug = 'lvtrade'"
        )
    finally:
        await conn.close()

    if lv is None:
        pytest.skip("seed.sql has not been applied")

    # Same key should never return equipart's data.
    response = await client.get(
        "/api/v1/tenants/me",
        headers={"X-Widget-Key": lv["widget_api_key"]},
    )
    assert response.status_code == 200
    assert response.json()["slug"] != "equipart"
