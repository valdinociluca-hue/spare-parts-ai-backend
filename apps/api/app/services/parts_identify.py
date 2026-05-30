"""Module 1 — Parts Identification core flow.

    query → embed (OpenAI) → Pinecone tenant-namespaced search
          → top-K Postgres rows → tenant's LLM (Yandex or Claude)
          → ranked JSON with reasoning, stock, prices.

Designed to be runnable from both the FastAPI route (asyncpg connection)
and standalone scripts (Supabase REST). The data-fetching is injected via
the ``ProductFetcher`` callable so both paths share the rest of the logic.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Awaitable, Callable

from app.embeddings import EmbeddingsPipeline, VectorMatch
from app.llm import BaseLLMClient, ChatMessage, CompletionResponse

logger = logging.getLogger(__name__)

ProductFetcher = Callable[[str, list[str]], Awaitable[list[dict]]]
"""(tenant_id, skus) -> list of product dicts with at least
sku, name, brand, qty_stock, price_base, currency, manufacturer_part_number."""


@dataclass(slots=True)
class IdentifyMatch:
    sku: str
    name: str
    brand: str | None
    manufacturer_part_number: str | None
    score: float
    stock: float
    price: float | None
    currency: str
    reasoning: str


@dataclass(slots=True)
class IdentifyResult:
    matches: list[IdentifyMatch]
    llm_raw: str
    completion: CompletionResponse
    tenant_id: str
    provider: str
    model: str


def _system_prompt(language: str, currency: str) -> str:
    """Tenant-scoped system prompt. Tells the LLM to answer in the tenant's
    language and to return strict JSON only."""
    lang_word = {
        "ru": "русском языке",
        "en": "English",
        "it": "italiano",
        "de": "Deutsch",
        "fr": "français",
    }.get(language, language)

    if language == "ru":
        return (
            "Ты — эксперт по запчастям для профессионального оборудования HoReCa. "
            "Тебе дают запрос пользователя и список из нескольких кандидатов-запчастей "
            "из каталога ОДНОГО конкретного дистрибьютора. Твоя задача — "
            "выбрать наиболее подходящие SKU и кратко объяснить почему. "
            f"Отвечай строго в {lang_word}. Цены указаны в валюте {currency}. "
            "Никогда не предлагай SKU, которых нет в списке кандидатов. "
            "Если ничего не подходит — верни пустой список. "
            "Возвращай ТОЛЬКО валидный JSON без какого-либо текста до или после."
        )
    return (
        "You are a spare-parts identification expert for professional HoReCa "
        "equipment. You receive the user's question and a list of candidate "
        "parts taken from ONE specific distributor's catalogue. Pick the SKUs "
        "that best match and briefly explain why. "
        f"Reply in {lang_word}. Prices are in {currency}. "
        "Never suggest a SKU that is not in the candidate list. "
        "If nothing matches, return an empty list. "
        "Return ONLY valid JSON, with no prose before or after."
    )


def _user_prompt(query: str, candidates: list[dict]) -> str:
    """Inject the catalog candidates plus the JSON schema we want back."""
    lines: list[str] = [f"USER QUERY: {query}", "", "CANDIDATE PARTS:"]
    for i, c in enumerate(candidates, 1):
        compatible = ", ".join(c.get("compatible_models") or []) or "—"
        lines.append(
            f"{i}. SKU={c['sku']} | brand={c.get('brand') or '—'} "
            f"| MPN={c.get('manufacturer_part_number') or '—'} "
            f"| name={c.get('name')}"
        )
        lines.append(f"   compatible: {compatible}")
        if c.get("description"):
            lines.append(f"   description: {c['description']}")
        lines.append(
            f"   stock={c.get('qty_stock', 0)} | price={c.get('price_base')} "
            f"{c.get('currency')}"
        )
    lines.extend(
        [
            "",
            "Return JSON with this exact shape:",
            json.dumps(
                {
                    "matches": [
                        {
                            "sku": "<one of the candidate SKUs>",
                            "reasoning": "<one short sentence>",
                        }
                    ]
                },
                indent=2,
            ),
            "Order matches by relevance (best first). Maximum 5 matches.",
        ]
    )
    return "\n".join(lines)


_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def _extract_json(text: str) -> dict:
    """LLMs sometimes wrap JSON in markdown fences or trailing prose; pull
    out the first JSON object we can find."""
    fenced = _JSON_FENCE_RE.search(text)
    if fenced:
        candidate = fenced.group(1).strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    logger.warning("could not parse JSON from LLM output: %s", text[:300])
    return {"matches": []}


async def identify_parts(
    *,
    tenant_id: str,
    tenant_language: str,
    tenant_currency: str,
    query: str,
    embeddings: EmbeddingsPipeline,
    llm: BaseLLMClient,
    fetch_products: ProductFetcher,
    top_k: int = 5,
) -> IdentifyResult:
    """End-to-end identification flow. Returns ranked matches with reasoning
    plus the raw completion (for logging / token accounting)."""
    vector_matches = await embeddings.query(
        tenant_id=tenant_id, query_text=query, top_k=top_k
    )
    if not vector_matches:
        completion = CompletionResponse(
            content="{\"matches\": []}",
            tokens_used=0,
            provider="stub",
            model="n/a",
        )
        return IdentifyResult(
            matches=[],
            llm_raw=completion.content,
            completion=completion,
            tenant_id=tenant_id,
            provider=str(llm.provider),
            model=getattr(llm, "model", ""),
        )

    skus = [m.sku for m in vector_matches]
    products = await fetch_products(tenant_id, skus)

    # Preserve Pinecone's relevance order.
    score_by_sku = {m.sku: m.score for m in vector_matches}
    products.sort(key=lambda p: -score_by_sku.get(p["sku"], 0.0))

    messages = [
        ChatMessage(role="system", content=_system_prompt(tenant_language, tenant_currency)),
        ChatMessage(role="user", content=_user_prompt(query, products)),
    ]
    completion = await llm.chat(messages=messages, temperature=0.1, max_tokens=900)

    parsed = _extract_json(completion.content)
    by_sku = {p["sku"]: p for p in products}

    matches: list[IdentifyMatch] = []
    for entry in parsed.get("matches", []) or []:
        sku = entry.get("sku")
        product = by_sku.get(sku)
        if not product:
            continue
        matches.append(
            IdentifyMatch(
                sku=product["sku"],
                name=product.get("name") or "",
                brand=product.get("brand"),
                manufacturer_part_number=product.get("manufacturer_part_number"),
                score=score_by_sku.get(sku, 0.0),
                stock=float(product.get("qty_stock") or 0),
                price=(
                    float(product["price_base"])
                    if product.get("price_base") is not None
                    else None
                ),
                currency=product.get("currency") or tenant_currency,
                reasoning=str(entry.get("reasoning") or "").strip(),
            )
        )

    return IdentifyResult(
        matches=matches,
        llm_raw=completion.content,
        completion=completion,
        tenant_id=tenant_id,
        provider=str(llm.provider),
        model=getattr(llm, "model", ""),
    )
