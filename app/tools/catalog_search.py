"""
app/tools/catalog_search.py — Tools for searching the spare parts catalog and equipment models.

Tools registered here:
  search_parts      — hybrid vector+BM25 search on spare_parts table
  get_part_details  — fetch one part by SKU
  search_equipment  — look up brands + equipment models by name
"""

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.schemas import ConversationContext
from app.db.models import Brand, EquipmentModel, SparePart
from app.rag.retriever import retrieve_parts
from app.tools.registry import BaseTool, tool_registry

logger = logging.getLogger(__name__)


class SearchPartsTool(BaseTool):
    name        = "search_parts"
    description = (
        "Поиск запчастей по запросу, модели оборудования или симптому неисправности. "
        "Используй, когда нужно найти подходящие запчасти по описанию проблемы или характеристикам."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query":      {"type": "string",  "description": "Поисковый запрос: симптом, название детали или неисправность"},
            "model_code": {"type": "string",  "description": "Код модели оборудования (если известен)"},
            "brand_slug": {"type": "string",  "description": "Slug бренда (например: electrolux, rational, bain-marie)"},
            "top_k":      {"type": "integer", "description": "Количество результатов (по умолчанию 5)", "default": 5},
        },
        "required": ["query"],
    }

    async def execute(
        self,
        args: dict[str, Any],
        session: AsyncSession,
        context: ConversationContext,
    ) -> dict[str, Any]:
        query      = args["query"]
        model_code = args.get("model_code") or context.equipment.model_code
        brand_slug = args.get("brand_slug")
        top_k      = min(int(args.get("top_k", 5)), 10)

        results = await retrieve_parts(
            session, query, top_k=top_k,
            brand_slug=brand_slug, model_code=model_code,
        )

        if not results:
            return {"found": 0, "parts": [], "message": "Запчасти не найдены по данному запросу."}

        return {
            "found": len(results),
            "parts": [
                {
                    "sku":               r.sku,
                    "name":              r.name,
                    "description":       r.description,
                    "brand":             r.brand,
                    "category":          r.category,
                    "price":             r.price,
                    "in_stock":          (r.stock_qty or 0) > 0,
                    "compatible_models": r.compatible_models,
                    "url":               r.source_url,
                    "relevance":         round(r.score, 3),
                }
                for r in results
            ],
        }


class GetPartDetailsTool(BaseTool):
    name        = "get_part_details"
    description = (
        "Получить подробную информацию о конкретной запчасти по артикулу (SKU). "
        "Используй, когда пользователь уточнил нужный артикул или когда нужно проверить наличие/цену."
    )
    parameters = {
        "type": "object",
        "properties": {
            "sku": {"type": "string", "description": "Артикул запчасти"},
        },
        "required": ["sku"],
    }

    async def execute(
        self,
        args: dict[str, Any],
        session: AsyncSession,
        context: ConversationContext,
    ) -> dict[str, Any]:
        sku = args["sku"].strip()
        part = await session.get(SparePart, sku)

        if not part:
            return {"found": False, "message": f"Запчасть с артикулом {sku!r} не найдена."}

        return {
            "found":             True,
            "sku":               part.sku,
            "name":              part.name,
            "description":       part.description,
            "category":          part.category,
            "price":             float(part.price) if part.price else None,
            "stock_qty":         part.stock_qty,
            "in_stock":          (part.stock_qty or 0) > 0,
            "compatible_models": part.compatible_models or [],
            "metadata":          part.metadata_ or {},
        }


class SearchEquipmentTool(BaseTool):
    name        = "search_equipment"
    description = (
        "Найти информацию о модели оборудования по названию или коду. "
        "Используй, когда пользователь называет марку или модель оборудования — "
        "нужно подтвердить, что такая модель есть в базе, и уточнить её код."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Название бренда или модели оборудования"},
        },
        "required": ["query"],
    }

    async def execute(
        self,
        args: dict[str, Any],
        session: AsyncSession,
        context: ConversationContext,
    ) -> dict[str, Any]:
        query = args["query"].strip()

        # Search brands
        brand_stmt = select(Brand).where(
            Brand.name.ilike(f"%{query}%") | Brand.slug.ilike(f"%{query}%")
        ).limit(5)
        brands = (await session.execute(brand_stmt)).scalars().all()

        # Search equipment models
        model_stmt = select(EquipmentModel).where(
            EquipmentModel.model_name.ilike(f"%{query}%") |
            EquipmentModel.model_code.ilike(f"%{query}%") |
            EquipmentModel.series.ilike(f"%{query}%")
        ).limit(10)
        models = (await session.execute(model_stmt)).scalars().all()

        if not brands and not models:
            return {
                "found": False,
                "message": f"Оборудование '{query}' не найдено в базе. Уточните марку или модель.",
            }

        return {
            "found":  True,
            "brands": [{"id": b.id, "name": b.name, "slug": b.slug} for b in brands],
            "models": [
                {
                    "id":         m.id,
                    "brand_id":   m.brand_id,
                    "model_name": m.model_name,
                    "model_code": m.model_code,
                    "series":     m.series,
                }
                for m in models
            ],
        }


# Register all catalog tools
tool_registry.register(SearchPartsTool())
tool_registry.register(GetPartDetailsTool())
tool_registry.register(SearchEquipmentTool())
