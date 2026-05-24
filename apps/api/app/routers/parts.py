from fastapi import APIRouter, Depends
import asyncpg

from app.deps import CurrentTenant, Tenant, get_connection
from app.schemas import IdentifyRequest, ProductMatch, SearchRequest, SearchResponse
from app.schemas.parts import IdentifyResponse

router = APIRouter(prefix="/parts", tags=["parts"])


@router.post("/identify", response_model=IdentifyResponse)
async def identify(
    payload: IdentifyRequest,
    tenant: Tenant = CurrentTenant,
    conn: asyncpg.Connection = Depends(get_connection),
) -> IdentifyResponse:
    """Module 1: AI Parts Identification.

    Phase 1 scaffold returns an empty list. Week 2 step 9 wires:
      1. Embed payload.query (OpenAI)
      2. Pinecone search filtered by namespace=tenant.id
      3. Pull top-N rows from public.products
      4. LLM router → rank + explain with the tenant's provider
    """
    _ = tenant, conn, payload
    return IdentifyResponse(matches=[])


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
