"""
app/tools/document_search.py — Single tool for technical documentation lookup.

  find_documents_for_model — semantic search over manuals, specs, and diagrams
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.schemas import ConversationContext
from app.rag.retriever import retrieve_docs
from app.tools.registry import BaseTool, tool_registry

logger = logging.getLogger(__name__)


class FindDocumentsForModelTool(BaseTool):
    name        = "find_documents_for_model"
    description = (
        "Найти техническую документацию, схемы или инструкции для модели оборудования. "
        "Используй, когда нужны: сборочная схема, список деталей, инструкция по обслуживанию "
        "или техническое описание."
    )
    parameters = {
        "type": "object",
        "properties": {
            "model_code": {
                "type": "string",
                "description": "Код или название модели оборудования",
            },
            "query": {
                "type": "string",
                "description": "Что именно найти: 'схема', 'список деталей', 'инструкция', и т.д.",
            },
        },
        "required": ["model_code", "query"],
    }

    async def execute(
        self,
        args: dict[str, Any],
        session: AsyncSession,
        context: ConversationContext,
    ) -> dict[str, Any]:
        model_code = args["model_code"]
        query      = f"{model_code} {args['query']}"

        results = await retrieve_docs(session, query, top_k=4)

        if not results:
            return {
                "found":   0,
                "message": f"Документация для модели «{model_code}» не найдена в базе.",
            }

        return {
            "found": len(results),
            "documents": [
                {
                    "title":        r.title,
                    "content":      r.content[:600],
                    "section_type": r.section_type,
                    "page":         r.page_num,
                    "url":          r.source_url,
                }
                for r in results
            ],
        }


tool_registry.register(FindDocumentsForModelTool())
