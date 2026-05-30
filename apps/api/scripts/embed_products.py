"""Generate embeddings for every product in Postgres and upsert to Pinecone.

Reads products through the Supabase REST API (service-role key) — so this
script does not need the DATABASE_URL password to be set. RLS is bypassed
by the service-role key.

Run:
    DYLD_LIBRARY_PATH=/opt/homebrew/opt/expat/lib \
        apps/api/.venv/bin/python apps/api/scripts/embed_products.py
"""

from __future__ import annotations

import asyncio
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
from app.embeddings import EmbeddingsPipeline, ProductDoc  # noqa: E402


async def fetch_products(tenant_slug: str) -> tuple[str, list[dict]]:
    base = settings.supabase_url.rstrip("/")
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Accept": "application/json",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        t = await client.get(
            f"{base}/rest/v1/tenants",
            params={"slug": f"eq.{tenant_slug}", "select": "id"},
            headers=headers,
        )
        t.raise_for_status()
        tenants = t.json()
        if not tenants:
            raise RuntimeError(f"tenant {tenant_slug} not found")
        tenant_id = tenants[0]["id"]

        p = await client.get(
            f"{base}/rest/v1/products",
            params={
                "tenant_id": f"eq.{tenant_id}",
                "select": "sku,name,description,brand,manufacturer,manufacturer_part_number,category,compatible_models",
            },
            headers=headers,
        )
        p.raise_for_status()
        return tenant_id, p.json()


async def main() -> None:
    pipe = EmbeddingsPipeline(
        openai_api_key=settings.openai_api_key,
        pinecone_api_key=settings.pinecone_api_key,
        pinecone_index=settings.pinecone_index,
        embedding_model=settings.openai_embedding_model,
        embedding_dim=settings.openai_embedding_dim,
    )

    for slug in ("lvtrade", "equipart"):
        tenant_id, products = await fetch_products(slug)
        await pipe.delete_tenant(tenant_id)
        docs = [
            ProductDoc(
                tenant_id=tenant_id,
                sku=p["sku"],
                name=p["name"],
                description=p.get("description"),
                brand=p.get("brand"),
                category=p.get("category"),
                manufacturer=p.get("manufacturer"),
                manufacturer_part_number=p.get("manufacturer_part_number"),
                compatible_models=p.get("compatible_models") or [],
            )
            for p in products
        ]
        written = await pipe.upsert_products(docs)
        print(
            f"[{slug}] tenant_id={tenant_id} products={len(products)} "
            f"vectors_written={written}"
        )


if __name__ == "__main__":
    asyncio.run(main())
