"""
app/tools/catalog_search.py — Two catalog lookup tools.

  find_part_by_article  — exact DB lookup by SKU/article number
  find_parts_for_model  — vector search filtered by brand + model code
"""

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.schemas import ConversationContext
from app.db.models import SparePart
from app.rag.retriever import retrieve_parts
from app.tools.registry import BaseTool, tool_registry

logger = logging.getLogger(__name__)


class FindPartByArticleTool(BaseTool):
    name        = "find_part_by_article"
    description = (
        "Найти запчасть по точному артикулу или коду детали. "
        "Используй, когда пользователь называет конкретный артикул или номер детали."
    )
    parameters = {
        "type": "object",
        "properties": {
            "article": {
                "type": "string",
                "description": "Артикул или код запчасти (например: 50286049001, ERC-COMP-07)",
            },
        },
        "required": ["article"],
    }

    async def execute(
        self,
        args: dict[str, Any],
        session: AsyncSession,
        context: ConversationContext,
    ) -> dict[str, Any]:
        article = args["article"].strip()

        # Exact match first
        part = await session.get(SparePart, article)

        # Case-insensitive fallback
        if not part:
            stmt = select(SparePart).where(
                SparePart.sku.ilike(article)
            ).limit(1)
            part = (await session.execute(stmt)).scalar_one_or_none()

        if not part:
            return {
                "found":   False,
                "message": f"Артикул «{article}» не найден в базе. Проверьте правильность написания.",
            }

        return {
            "found":             True,
            "sku":               part.sku,
            "name":              part.name,
            "description":       part.description,
            "category":          part.category,
            "price":             float(part.price) if part.price else None,
            "in_stock":          (part.stock_qty or 0) > 0,
            "stock_qty":         part.stock_qty,
            "compatible_models": part.compatible_models or [],
            "url":               (part.metadata_ or {}).get("source_url"),
        }


class FindPartsForModelTool(BaseTool):
    name        = "find_parts_for_model"
    description = (
        "Найти запчасти для конкретной модели оборудования по описанию проблемы или симптому. "
        "Используй, когда известны марка и/или модель оборудования и есть описание неисправности."
    )
    parameters = {
        "type": "object",
        "properties": {
            "problem_description": {
                "type": "string",
                "description": "Описание проблемы или неисправности (например: не охлаждает, течёт компрессор)",
            },
            "brand": {
                "type": "string",
                "description": "Марка оборудования (например: Electrolux, Rational)",
            },
            "model_code": {
                "type": "string",
                "description": "Код или название модели (например: ERC 3711, SCC WE 61)",
            },
        },
        "required": ["problem_description"],
    }

    async def execute(
        self,
        args: dict[str, Any],
        session: AsyncSession,
        context: ConversationContext,
    ) -> dict[str, Any]:
        query      = args["problem_description"]
        brand      = args.get("brand") or context.equipment.brand
        model_code = args.get("model_code") or context.equipment.model_code

        # Enrich query with context for better vector match
        if brand or model_code:
            query = f"{brand or ''} {model_code or ''} {query}".strip()

        brand_slug = brand.lower().replace(" ", "-") if brand else None

        results = await retrieve_parts(
            session, query, top_k=5,
            brand_slug=brand_slug,
            model_code=model_code,
        )

        # Update context with found SKUs
        if results:
            context.candidate_skus = [r.sku for r in results[:3]]
            context.last_confidence = results[0].score if results else None

        if not results:
            return {
                "found":   0,
                "parts":   [],
                "message": "Запчасти не найдены. Уточните модель оборудования или симптом.",
            }

        return {
            "found": len(results),
            "parts": [
                {
                    "sku":        r.sku,
                    "name":       r.name,
                    "description": r.description,
                    "price":      r.price,
                    "in_stock":   (r.stock_qty or 0) > 0,
                    "url":        r.source_url,
                    "relevance":  round(r.score, 2),
                }
                for r in results
            ],
        }


tool_registry.register(FindPartByArticleTool())
tool_registry.register(FindPartsForModelTool())
