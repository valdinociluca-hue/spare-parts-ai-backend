"""
app/tools/error_code_search.py — Fault-code lookup tool.

  decode_error_code — given a brand, an error/fault code and (optionally)
  a model, return the likely cause, severity, recommended solution and
  the spare-part SKUs that typically resolve it (resolved to live
  catalogue rows so stock + price are included).

model_pattern in the error_codes table is a shell-style glob ("SCC*",
"Appia*", "*") matched case-insensitively against the model code.
"""

import fnmatch
import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.schemas import ConversationContext
from app.db.models import ErrorCode, SparePart
from app.tools.registry import BaseTool, tool_registry

logger = logging.getLogger(__name__)


class DecodeErrorCodeTool(BaseTool):
    name        = "decode_error_code"
    description = (
        "Расшифровать код ошибки оборудования и подобрать запчасти для его устранения. "
        "Используй, когда пользователь называет код ошибки (например: E5, F3, Err 10) "
        "и марку оборудования."
    )
    parameters = {
        "type": "object",
        "properties": {
            "brand": {
                "type": "string",
                "description": "Марка оборудования (например: Rational, Unox, Nuova Simonelli)",
            },
            "error_code": {
                "type": "string",
                "description": "Код ошибки как он отображается на дисплее (например: E5, F3, Err 10)",
            },
            "model_code": {
                "type": "string",
                "description": "Код или название модели, если известно (например: SCC 61, Appia)",
            },
        },
        "required": ["brand", "error_code"],
    }

    async def execute(
        self,
        args: dict[str, Any],
        session: AsyncSession,
        context: ConversationContext,
    ) -> dict[str, Any]:
        brand      = (args.get("brand") or context.equipment.brand or "").strip()
        code       = (args.get("error_code") or "").strip()
        model_code = (args.get("model_code") or context.equipment.model_code or "").strip()

        if not brand or not code:
            return {
                "found":   False,
                "message": "Укажите марку оборудования и код ошибки.",
            }

        # Match brand + error_code case-insensitively; brand stored normalised
        # ("NUOVA_SIMONELLI") or free-form — compare on a squashed form.
        brand_norm = brand.upper().replace(" ", "_")
        stmt = (
            select(ErrorCode)
            .where(func.upper(func.replace(ErrorCode.brand, " ", "_")) == brand_norm)
            .where(func.upper(ErrorCode.error_code) == code.upper())
        )
        rows = (await session.execute(stmt)).scalars().all()

        if not rows:
            return {
                "found":   False,
                "message": (
                    f"Код «{code}» для бренда {brand} не найден в базе. "
                    "Рекомендую связаться с менеджером для уточнения."
                ),
            }

        # Prefer the row whose model_pattern matches the given model.
        match = self._best_match(rows, model_code)

        parts = await self._resolve_parts(session, match.likely_parts or [])
        if parts:
            context.candidate_skus = [p["sku"] for p in parts[:3]]

        return {
            "found":       True,
            "brand":       match.brand,
            "error_code":  match.error_code,
            "description": match.description,
            "severity":    match.severity,
            "solution":    match.solution,
            "parts":       parts,
        }

    @staticmethod
    def _best_match(rows: list[ErrorCode], model_code: str) -> ErrorCode:
        if model_code:
            mc = model_code.upper()
            for r in rows:
                pat = (r.model_pattern or "*").upper()
                if fnmatch.fnmatch(mc, pat):
                    return r
        # Fall back to the most specific (non-"*") pattern, else first row.
        specific = [r for r in rows if (r.model_pattern or "*") != "*"]
        return (specific or rows)[0]

    @staticmethod
    async def _resolve_parts(session: AsyncSession, skus: list[str]) -> list[dict]:
        if not skus:
            return []
        stmt = select(SparePart).where(SparePart.sku.in_(skus))
        found = {p.sku: p for p in (await session.execute(stmt)).scalars().all()}
        out: list[dict] = []
        for sku in skus:
            p = found.get(sku)
            if p:
                out.append({
                    "sku":       p.sku,
                    "name":      p.name,
                    "price":     float(p.price) if p.price else None,
                    "in_stock":  (p.stock_qty or 0) > 0,
                    "stock_qty": p.stock_qty or 0,
                })
            else:
                # SKU referenced by the fault DB but not yet in the catalogue.
                out.append({"sku": sku, "name": None, "in_stock": False,
                            "stock_qty": 0, "price": None})
        return out


tool_registry.register(DecodeErrorCodeTool())
