"""
app/tools/document_search.py — Tools for searching technical documentation and diagrams.
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.schemas import ConversationContext
from app.rag.retriever import retrieve_docs
from app.tools.registry import BaseTool, tool_registry

logger = logging.getLogger(__name__)


class SearchDocsTool(BaseTool):
    name        = "search_docs"
    description = (
        "Поиск в технической документации: инструкции, руководства по техобслуживанию, "
        "спецификации. Используй, когда пользователь спрашивает о технических характеристиках, "
        "процедурах ремонта или когда нужно найти описание неисправности в документации."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query":    {"type": "string", "description": "Поисковый запрос по документации"},
            "model_id": {"type": "string", "description": "ID модели оборудования (если известен)"},
        },
        "required": ["query"],
    }

    async def execute(
        self,
        args: dict[str, Any],
        session: AsyncSession,
        context: ConversationContext,
    ) -> dict[str, Any]:
        query    = args["query"]
        model_id = args.get("model_id")

        results = await retrieve_docs(session, query, top_k=4, model_id=model_id)

        if not results:
            return {"found": 0, "chunks": [], "message": "Документация по данному запросу не найдена."}

        return {
            "found": len(results),
            "chunks": [
                {
                    "chunk_id":     r.chunk_id,
                    "title":        r.title,
                    "content":      r.content[:800],   # truncate for prompt safety
                    "section_type": r.section_type,
                    "page":         r.page_num,
                    "source_url":   r.source_url,
                    "relevance":    round(r.score, 3),
                }
                for r in results
            ],
        }


class GetDiagramsTool(BaseTool):
    name        = "get_diagrams"
    description = (
        "Найти сборочные чертежи и детальные схемы для конкретной модели оборудования. "
        "Используй, когда пользователю нужна схема для определения нужной детали."
    )
    parameters = {
        "type": "object",
        "properties": {
            "model_code": {"type": "string", "description": "Код модели оборудования"},
        },
        "required": ["model_code"],
    }

    async def execute(
        self,
        args: dict[str, Any],
        session: AsyncSession,
        context: ConversationContext,
    ) -> dict[str, Any]:
        model_code = args["model_code"]

        results = await retrieve_docs(
            session,
            query=f"схема детали {model_code} diagram",
            top_k=4,
            section_type="diagram",
        )

        if not results:
            return {
                "found": 0,
                "message": f"Схемы для модели {model_code!r} не найдены в базе.",
            }

        return {
            "found": len(results),
            "diagrams": [
                {
                    "chunk_id":   r.chunk_id,
                    "title":      r.title,
                    "source_url": r.source_url,
                    "page":       r.page_num,
                    "content":    r.content[:400],
                }
                for r in results
            ],
        }


tool_registry.register(SearchDocsTool())
tool_registry.register(GetDiagramsTool())
