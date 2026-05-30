"""End-to-end test for /parts/identify against both tenants.

Runs the exact same service code the FastAPI route runs (``identify_parts``),
but reads candidate products via Supabase REST so it does not require
DATABASE_URL to carry a real password.

For each tenant, prints:
  - the resolved tenant + provider + model
  - the full structured response (matches with SKU, brand, score, stock,
    price, reasoning)
  - the raw LLM JSON the matches came from
  - token usage + dollar-equivalent cost estimate
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import httpx

APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

REPO_ROOT = APP_ROOT.parents[1]
ENV_FILE = REPO_ROOT / ".env"
if ENV_FILE.exists():
    for line in ENV_FILE.read_text().splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

from app.config import settings  # noqa: E402
from app.embeddings import EmbeddingsPipeline  # noqa: E402
from app.llm.claude import ClaudeClient  # noqa: E402
from app.llm.yandex import YandexGPTClient  # noqa: E402
from app.services import identify_parts  # noqa: E402

# Rough USD pricing per 1M tokens — used only for "feel" of cost in output.
PRICE_PER_M_TOKENS = {
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0, "blended": 7.5},
    # YandexGPT Pro RU pricing (~0.40 ₽ / 1k tokens ≈ ~$4.40 / 1M tokens).
    "yandexgpt": {"input": 4.4, "output": 4.4, "blended": 4.4},
}
EMBED_PRICE_PER_M_TOKENS = 0.02  # text-embedding-3-small


def _estimate_cost(model: str, tokens: int) -> float:
    blended = PRICE_PER_M_TOKENS.get(model, {}).get("blended", 5.0)
    return tokens / 1_000_000 * blended


class SupabaseRestFetcher:
    """Drop-in replacement for the asyncpg fetcher used by FastAPI: reads
    candidate products through Supabase's PostgREST endpoint using the
    service-role key (RLS bypass). Same return shape as the live route."""

    def __init__(self) -> None:
        self.base = settings.supabase_url.rstrip("/")
        self.headers = {
            "apikey": settings.supabase_service_role_key,
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
            "Accept": "application/json",
        }

    async def __call__(self, tenant_id: str, skus: list[str]) -> list[dict]:
        if not skus:
            return []
        params = {
            "tenant_id": f"eq.{tenant_id}",
            "sku": f"in.({','.join(skus)})",
            "select": (
                "sku,name,description,brand,manufacturer,"
                "manufacturer_part_number,category,compatible_models,"
                "qty_stock,price_base,currency"
            ),
        }
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(
                f"{self.base}/rest/v1/products",
                params=params,
                headers=self.headers,
            )
            r.raise_for_status()
            return r.json()


async def _fetch_tenant(slug: str) -> dict:
    base = settings.supabase_url.rstrip("/")
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(
            f"{base}/rest/v1/tenants",
            params={
                "slug": f"eq.{slug}",
                "select": "id,slug,name,language,currency,llm_provider",
            },
            headers=headers,
        )
        r.raise_for_status()
        rows = r.json()
        if not rows:
            raise RuntimeError(f"tenant {slug} not found")
        return rows[0]


async def run_case(slug: str, query: str) -> None:
    tenant = await _fetch_tenant(slug)

    if tenant["llm_provider"] == "yandex":
        llm = YandexGPTClient(
            api_key=settings.yandex_api_key,
            folder_id=settings.yandex_folder_id,
            model=settings.yandex_gpt_model,
        )
    else:
        llm = ClaudeClient(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
        )

    pipe = EmbeddingsPipeline(
        openai_api_key=settings.openai_api_key,
        pinecone_api_key=settings.pinecone_api_key,
        pinecone_index=settings.pinecone_index,
        embedding_model=settings.openai_embedding_model,
        embedding_dim=settings.openai_embedding_dim,
    )

    fetcher = SupabaseRestFetcher()

    print("\n" + "=" * 80)
    print(f"TENANT  : {tenant['slug']} ({tenant['name']}) "
          f"lang={tenant['language']} ccy={tenant['currency']} "
          f"provider={tenant['llm_provider']} model={getattr(llm, 'model', '')}")
    print(f"QUERY   : {query}")
    print("=" * 80)

    result = await identify_parts(
        tenant_id=tenant["id"],
        tenant_language=tenant["language"],
        tenant_currency=tenant["currency"],
        query=query,
        embeddings=pipe,
        llm=llm,
        fetch_products=fetcher,
        top_k=5,
    )

    response_body = {
        "matches": [
            {
                "sku": m.sku,
                "name": m.name,
                "brand": m.brand,
                "manufacturer_part_number": m.manufacturer_part_number,
                "score": round(m.score, 4),
                "stock": m.stock,
                "price": m.price,
                "currency": m.currency,
                "reasoning": m.reasoning,
            }
            for m in result.matches
        ],
        "usage": {
            "provider": result.provider,
            "model": result.model,
            "tokens_used": result.completion.tokens_used,
        },
    }
    print("API RESPONSE BODY:")
    print(json.dumps(response_body, ensure_ascii=False, indent=2))

    leaked = [m.sku for m in result.matches if not m.sku.startswith(
        "LV-" if slug == "lvtrade" else "EQ-"
    )]
    print(f"\nLEAKED SKUS FROM OTHER TENANT: {leaked or 'none'}")

    print("\nRAW LLM OUTPUT:")
    print(result.llm_raw)

    cost_usd = _estimate_cost(result.completion.model, result.completion.tokens_used)
    # Embeddings cost is tiny but include it for completeness.
    cost_usd += (len(query.split()) * 2) / 1_000_000 * EMBED_PRICE_PER_M_TOKENS

    print(
        f"\nCOST: ~${cost_usd:.6f}  "
        f"({result.completion.tokens_used} tokens via {result.provider}/{result.completion.model})"
    )


async def main() -> None:
    await run_case("lvtrade",  "нужен насос Rational")
    await run_case("equipart", "need pump for Rational")


if __name__ == "__main__":
    asyncio.run(main())
