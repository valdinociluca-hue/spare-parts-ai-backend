"""
app/rag/vector_store.py — pgvector-backed similarity search via SQLAlchemy.

Handles both spare_parts and document_chunks tables, each with a Vector(768) column.
"""

import logging
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.schemas import DocumentResult, PartResult
from app.db.models import DocumentChunk, DocumentSource, SparePart, Brand

logger = logging.getLogger(__name__)


async def search_parts_by_vector(
    session: AsyncSession,
    vector: list[float],
    top_k: int = 8,
    brand_slug: Optional[str] = None,
    model_code: Optional[str] = None,
) -> list[PartResult]:
    """
    Cosine similarity search on spare_parts.embedding.
    Optional filters: brand_slug, model_code (substring match on compatible_models).
    """
    # Build base query — pgvector operator <=> = cosine distance
    q = (
        select(SparePart, (1 - SparePart.embedding.cosine_distance(vector)).label("score"))
        .where(SparePart.embedding.isnot(None))
        .order_by(SparePart.embedding.cosine_distance(vector))
        .limit(top_k)
    )

    if brand_slug:
        q = q.join(Brand, SparePart.brand_id == Brand.id).where(Brand.slug == brand_slug)

    if model_code:
        q = q.where(text("compatible_models @> ARRAY[:mc]").bindparams(mc=model_code))

    rows = (await session.execute(q)).all()

    results = []
    for part, score in rows:
        results.append(PartResult(
            sku=part.sku,
            name=part.name,
            description=part.description,
            brand=part.brand.name if part.brand else None,
            category=part.category,
            price=float(part.price) if part.price else None,
            stock_qty=part.stock_qty,
            compatible_models=part.compatible_models or [],
            source_url=(part.metadata_ or {}).get("source_url"),
            score=float(score) if score else 0.0,
        ))
    return results


async def search_docs_by_vector(
    session: AsyncSession,
    vector: list[float],
    top_k: int = 5,
    section_type: Optional[str] = None,
    model_id: Optional[str] = None,
) -> list[DocumentResult]:
    """
    Cosine similarity search on document_chunks.embedding.
    """
    q = (
        select(
            DocumentChunk,
            DocumentSource,
            (1 - DocumentChunk.embedding.cosine_distance(vector)).label("score"),
        )
        .join(DocumentSource, DocumentChunk.source_id == DocumentSource.id)
        .where(DocumentChunk.embedding.isnot(None))
        .order_by(DocumentChunk.embedding.cosine_distance(vector))
        .limit(top_k)
    )

    if section_type:
        q = q.where(DocumentChunk.section_type == section_type)

    if model_id:
        q = q.where(DocumentSource.model_id == model_id)

    rows = (await session.execute(q)).all()

    results = []
    for chunk, source, score in rows:
        results.append(DocumentResult(
            chunk_id=chunk.id,
            source_url=source.source_url,
            title=source.title,
            content=chunk.content,
            section_type=chunk.section_type,
            page_num=chunk.page_num,
            score=float(score) if score else 0.0,
        ))
    return results
