from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

import asyncpg
from fastapi import Depends, Header, HTTPException, Query, Request, status
from jose import JWTError, jwt

from app.config import settings
from app.db.session import get_connection


@dataclass(frozen=True, slots=True)
class Tenant:
    """In-memory snapshot of a tenant row, attached to request.state.tenant."""

    id: UUID
    slug: str
    name: str
    region: Literal["RU", "GLOBAL"]
    llm_provider: Literal["yandex", "claude"]
    brand_color: str
    logo_url: str | None
    language: str
    plan: str


_TENANT_QUERY = """
    select id, slug, name, region, llm_provider, brand_color, logo_url, language, plan
    from public.tenants
    where {filter}
    limit 1
"""


async def _load_tenant_by(
    conn: asyncpg.Connection, *, column: str, value: object
) -> Tenant | None:
    if column not in {"id", "slug", "widget_api_key"}:
        raise ValueError(f"unsupported tenant lookup column: {column}")
    row = await conn.fetchrow(_TENANT_QUERY.format(filter=f"{column} = $1"), value)
    if row is None:
        return None
    return Tenant(
        id=row["id"],
        slug=row["slug"],
        name=row["name"],
        region=row["region"],
        llm_provider=row["llm_provider"],
        brand_color=row["brand_color"],
        logo_url=row["logo_url"],
        language=row["language"],
        plan=row["plan"],
    )


def _decode_jwt(token: str) -> dict[str, object]:
    """Decode the bearer token. In production this verifies against Supabase
    JWKS; for scaffold we accept HS256 signed with settings.jwt_secret.
    """
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token"
        ) from exc


async def get_current_tenant(
    request: Request,
    conn: asyncpg.Connection = Depends(get_connection),
    x_tenant_slug: str | None = Header(default=None, alias="X-Tenant-Slug"),
    x_widget_key: str | None = Header(default=None, alias="X-Widget-Key"),
    widget_key_qs: str | None = Query(default=None, alias="widget_key"),
    authorization: str | None = Header(default=None),
) -> Tenant:
    """Resolve the current tenant from one of:
      1. X-Tenant-Slug header (internal scripts; not yet auth-gated)
      2. X-Widget-Key header or ?widget_key= query param (embedded widget)
      3. Authorization: Bearer <jwt> with tenant_id claim (dashboard)

    Then SET LOCAL partsai.tenant_id so RLS policies can enforce isolation
    even if a handler forgets to filter by tenant_id.
    """
    tenant: Tenant | None = None

    if x_tenant_slug:
        tenant = await _load_tenant_by(conn, column="slug", value=x_tenant_slug)

    widget_key = x_widget_key or widget_key_qs
    if tenant is None and widget_key:
        tenant = await _load_tenant_by(conn, column="widget_api_key", value=widget_key)

    if tenant is None and authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        claims = _decode_jwt(token)
        tenant_id = claims.get("tenant_id")
        if isinstance(tenant_id, str):
            try:
                tenant = await _load_tenant_by(conn, column="id", value=UUID(tenant_id))
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="invalid tenant_id claim",
                ) from exc

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="no tenant context (provide X-Widget-Key, Authorization, or X-Tenant-Slug)",
        )

    # Tell Postgres which tenant this transaction is for. RLS reads this GUC.
    await conn.execute("select set_config('partsai.tenant_id', $1, true)", str(tenant.id))

    request.state.tenant = tenant
    return tenant


CurrentTenant = Depends(get_current_tenant)
