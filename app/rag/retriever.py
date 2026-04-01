"""
app/rag/retriever.py — Vector-only retrieval (pgvector cosine similarity).

MVP: no BM25, no RRF fusion. Pure vector search with optional metadata filters.
BM25 hybrid can be added later once the catalog is populated and benchmarked.
"""

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.schemas import DocumentResult, PartResult
from app.rag.embedder import embed
from app.rag.vector_store import search_docs_by_vector, search_parts_by_vector

logger = logging.getLogger(__name__)


async def retrieve_parts(
    session: AsyncSession,
    query: str,
    top_k: int = 6,
    brand_slug: Optional[str] = None,
    model_code: Optional[str] = None,
) -> list[PartResult]:
    query_vector = embed(query)
    return await search_parts_by_vector(
        session, query_vector, top_k=top_k,
        brand_slug=brand_slug, model_code=model_code,
    )


async def retrieve_docs(
    session: AsyncSession,
    query: str,
    top_k: int = 4,
    section_type: Optional[str] = None,
    model_id: Optional[str] = None,
) -> list[DocumentResult]:
    query_vector = embed(query)
    return await search_docs_by_vector(
        session, query_vector, top_k=top_k,
        section_type=section_type, model_id=model_id,
    )
