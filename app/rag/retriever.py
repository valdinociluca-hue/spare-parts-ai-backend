"""
app/rag/retriever.py — Hybrid BM25 + vector retrieval with Reciprocal Rank Fusion.

Two retrieval paths per query:
  1. Vector similarity  (semantic: catches synonyms, Russian/English mix)
  2. BM25 full-text     (lexical: catches exact SKUs, model codes, precise terms)

Results are merged with RRF (Reciprocal Rank Fusion) and deduplicated by SKU.
"""

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.schemas import DocumentResult, PartResult
from app.rag.embedder import embed
from app.rag.vector_store import search_docs_by_vector, search_parts_by_vector

logger = logging.getLogger(__name__)

_RRF_K = 60   # standard RRF constant


def _rrf_merge(ranked_lists: list[list[str]], scores_by_id: dict) -> list[str]:
    """
    Reciprocal Rank Fusion over multiple ranked lists of IDs.
    Returns a merged list sorted by combined RRF score descending.
    """
    rrf: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, doc_id in enumerate(ranked):
            rrf[doc_id] = rrf.get(doc_id, 0.0) + 1.0 / (_RRF_K + rank + 1)
    return sorted(rrf.keys(), key=lambda x: rrf[x], reverse=True)


async def retrieve_parts(
    session: AsyncSession,
    query: str,
    top_k: int = 6,
    brand_slug: Optional[str] = None,
    model_code: Optional[str] = None,
) -> list[PartResult]:
    """
    Hybrid retrieval for spare parts.
    Vector path always runs. BM25 path runs via Postgres tsvector if tsvector column exists.
    Falls back gracefully to vector-only if FTS index not available.
    """
    query_vector = embed(query)

    vector_results = await search_parts_by_vector(
        session, query_vector, top_k=top_k * 2,
        brand_slug=brand_slug, model_code=model_code,
    )

    # BM25 via Postgres tsvector — graceful fallback if column not indexed yet
    bm25_results: list[PartResult] = []
    try:
        from sqlalchemy import text as sa_text
        from app.db.models import SparePart
        stmt = sa_text("""
            SELECT sku, ts_rank(to_tsvector('russian', coalesce(name,'') || ' ' || coalesce(description,'')),
                                plainto_tsquery('russian', :q)) AS rank
            FROM spare_parts
            WHERE to_tsvector('russian', coalesce(name,'') || ' ' || coalesce(description,''))
                  @@ plainto_tsquery('russian', :q)
            ORDER BY rank DESC
            LIMIT :lim
        """)
        rows = (await session.execute(stmt, {"q": query, "lim": top_k * 2})).all()
        bm25_skus = {r.sku: r.rank for r in rows}

        if bm25_skus:
            stmt2 = select(SparePart).where(SparePart.sku.in_(bm25_skus.keys()))
            parts = (await session.execute(stmt2)).scalars().all()
            for p in parts:
                bm25_results.append(PartResult(
                    sku=p.sku, name=p.name, description=p.description,
                    category=p.category,
                    price=float(p.price) if p.price else None,
                    stock_qty=p.stock_qty,
                    compatible_models=p.compatible_models or [],
                    score=float(bm25_skus.get(p.sku, 0)),
                ))
    except Exception:
        logger.debug("BM25 path unavailable, using vector-only retrieval")

    if not bm25_results:
        return vector_results[:top_k]

    # RRF merge
    vec_ids  = [r.sku for r in vector_results]
    bm25_ids = [r.sku for r in bm25_results]
    merged_ids = _rrf_merge([vec_ids, bm25_ids], {})

    by_sku = {r.sku: r for r in vector_results + bm25_results}
    return [by_sku[sid] for sid in merged_ids[:top_k] if sid in by_sku]


async def retrieve_docs(
    session: AsyncSession,
    query: str,
    top_k: int = 4,
    section_type: Optional[str] = None,
    model_id: Optional[str] = None,
) -> list[DocumentResult]:
    """Vector-only retrieval for document chunks (manuals, specs, diagrams)."""
    query_vector = embed(query)
    return await search_docs_by_vector(
        session, query_vector, top_k=top_k,
        section_type=section_type, model_id=model_id,
    )
