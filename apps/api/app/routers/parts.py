from __future__ import annotations

import asyncpg
from fastapi import APIRouter, Depends

from app.deps import CurrentTenant, Tenant, get_connection
from app.embeddings import get_embeddings_pipeline
from app.llm.router import get_llm_for_tenant
from app.schemas import (
    IdentifyRequest,
    IdentifyResponse,
    ProductMatch,
    SearchRequest,
    SearchResponse,
    TokenUsage,
)
from app.services import identify_parts

router = APIRouter(prefix="/parts", tags=["parts"])


class _PgFetcher:
    """Closes over an asyncpg connection so the identify service can fetch
    candidate products without knowing about FastAPI."""

    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def __call__(self, tenant_id: str, skus: list[str]) -> list[dict]:
        if not skus:
            return []
        rows = await self._conn.fetch(
            """
            select sku, name, description, brand, manufacturer,
                   manufacturer_part_number, category, compatible_models,
                   qty_stock, price_base, currency
            from public.products
            where tenant_id = $1::uuid and sku = any($2::text[])
            """,
            tenant_id,
            skus,
        )
        return [dict(r) for r in rows]


@router.post("/identify", response_model=IdentifyResponse)
async def identify(
    payload: IdentifyRequest,
    tenant: Tenant = CurrentTenant,
    conn: asyncpg.Connection = Depends(get_connection),
) -> IdentifyResponse:
    """Module 1: AI Parts Identification.

    Pipeline:
      1. embed(payload.query) via OpenAI text-embedding-3-small
      2. Pinecone search in namespace=tenant.id with metadata tenant filter
      3. fetch top-K products from Postgres (RLS still scoped to this tenant)
      4. ask the tenant's LLM to rank + justify in the tenant's language
      5. return structured matches plus per-request token usage
    """
    pipeline = get_embeddings_pipeline()
    llm = get_llm_for_tenant(tenant)
    fetcher = _PgFetcher(conn)

    result = await identify_parts(
        tenant_id=str(tenant.id),
        tenant_language=tenant.language,
        tenant_currency=getattr(tenant, "currency", "EUR") or "EUR",
        query=payload.query,
        embeddings=pipeline,
        llm=llm,
        fetch_products=fetcher,
        top_k=5,
    )

    return IdentifyResponse(
        matches=[
            ProductMatch(
                sku=m.sku,
                name=m.name,
                brand=m.brand,
                manufacturer_part_number=m.manufacturer_part_number,
                score=m.score,
                stock=m.stock,
                price=m.price,
                currency=m.currency,
                reasoning=m.reasoning,
            )
            for m in result.matches
        ],
        usage=TokenUsage(
            provider=result.provider,
            model=result.model,
            tokens_used=result.completion.tokens_used,
        ),
    )


@router.post("/search", response_model=SearchResponse)
async def search(
    payload: SearchRequest,
    tenant: Tenant = CurrentTenant,
    conn: asyncpg.Connection = Depends(get_connection),
) -> SearchResponse:
    """Direct catalog search (no LLM). RLS enforces tenant isolation, so we
    don't need to add WHERE tenant_id = ... here — but we will anyway as
    defense-in-depth once the query is real."""
    _ = tenant, conn, payload
    return SearchResponse(products=[])
