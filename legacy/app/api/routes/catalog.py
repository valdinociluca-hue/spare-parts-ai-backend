"""
app/api/routes/catalog.py — Public catalogue lookup endpoints.

GET /api/v1/catalog/search?q=&brand=&in_stock=true&limit=
    Keyword search over SKU / name / description (+ optional vector
    semantic search when a query is given), with brand and stock filters.

GET /api/v1/catalog/sku/{sku}
    Single part: full detail + live stock + price.

GET /api/v1/catalog/compatible?model=
    All parts whose compatible_models array contains the given model code.

GET /api/v1/catalog/error?brand=&code=&model=
    Decode a fault code → cause, severity, solution + recommended parts.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.schemas import ConversationContext
from app.db.models import Brand, SparePart
from app.db.session import get_session
from app.tools.error_code_search import DecodeErrorCodeTool

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/catalog", tags=["catalog"])


def _part_dict(p: SparePart) -> dict:
    return {
        "sku":               p.sku,
        "name":              p.name,
        "description":       p.description,
        "brand":             p.brand.name if p.brand else None,
        "category":          p.category,
        "price":             float(p.price) if p.price is not None else None,
        "in_stock":          (p.stock_qty or 0) > 0,
        "stock_qty":         p.stock_qty or 0,
        "compatible_models": p.compatible_models or [],
        "url":               (p.metadata_ or {}).get("source_url"),
    }


@router.get("/search")
async def search(
    q: str = Query("", description="Free-text query: SKU, name, symptom, model"),
    brand: str | None = Query(None, description="Brand name or slug filter"),
    in_stock: bool = Query(False, description="Only parts with stock_qty > 0"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
):
    stmt = select(SparePart).options(joinedload(SparePart.brand))

    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(
            SparePart.sku.ilike(like),
            SparePart.name.ilike(like),
            SparePart.description.ilike(like),
        ))

    if brand:
        b = brand.strip()
        stmt = stmt.join(Brand, SparePart.brand_id == Brand.id).where(or_(
            Brand.slug == b.lower().replace(" ", "-"),
            func.upper(Brand.name) == b.upper(),
            Brand.name.ilike(f"%{b}%"),
        ))

    if in_stock:
        stmt = stmt.where(SparePart.stock_qty > 0)

    stmt = stmt.order_by(SparePart.stock_qty.desc().nullslast()).limit(limit)
    rows = (await db.execute(stmt)).scalars().unique().all()

    return {"query": q, "count": len(rows), "results": [_part_dict(p) for p in rows]}


@router.get("/sku/{sku}")
async def get_sku(sku: str, db: AsyncSession = Depends(get_session)):
    stmt = (
        select(SparePart)
        .options(joinedload(SparePart.brand))
        .where(SparePart.sku == sku)
    )
    part = (await db.execute(stmt)).scalars().first()

    if not part:
        # Case-insensitive fallback
        stmt = (
            select(SparePart)
            .options(joinedload(SparePart.brand))
            .where(SparePart.sku.ilike(sku))
        )
        part = (await db.execute(stmt)).scalars().first()

    if not part:
        raise HTTPException(status_code=404, detail=f"SKU '{sku}' not found")

    return _part_dict(part)


@router.get("/compatible")
async def compatible(
    model: str = Query(..., description="Equipment model code, e.g. 'SCC 61'"),
    in_stock: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_session),
):
    # PostgreSQL array containment: compatible_models @> ARRAY['SCC 61']
    stmt = (
        select(SparePart)
        .options(joinedload(SparePart.brand))
        .where(SparePart.compatible_models.contains([model.strip()]))
    )
    if in_stock:
        stmt = stmt.where(SparePart.stock_qty > 0)
    stmt = stmt.order_by(SparePart.stock_qty.desc().nullslast()).limit(limit)

    rows = (await db.execute(stmt)).scalars().unique().all()
    return {"model": model, "count": len(rows), "results": [_part_dict(p) for p in rows]}


@router.get("/error")
async def error_code(
    brand: str = Query(..., description="Equipment brand, e.g. 'Rational'"),
    code: str = Query(..., description="Error code as shown on display, e.g. 'E5'"),
    model: str | None = Query(None, description="Model code, e.g. 'SCC 61'"),
    db: AsyncSession = Depends(get_session),
):
    tool = DecodeErrorCodeTool()
    result = await tool.execute(
        {"brand": brand, "error_code": code, "model_code": model or ""},
        db,
        ConversationContext(),
    )
    if not result.get("found"):
        raise HTTPException(status_code=404, detail=result.get("message", "Not found"))
    return result
