"""Embeddings + Pinecone pipeline.

A single ``EmbeddingsPipeline`` owns:
  - OpenAI embedding generation (``text-embedding-3-small``, 1536-dim)
  - Pinecone upserts and queries against the single ``partsai-products``
    index, namespaced + filtered by ``tenant_id`` for hard isolation.

Tenant scoping is enforced two ways for defense-in-depth:
  1. Vectors are written into a per-tenant namespace (``tenant_id`` string).
  2. Every vector carries ``tenant_id`` in metadata, and queries also pass
     ``filter={"tenant_id": ...}`` so a mis-set namespace cannot leak across.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable

from openai import AsyncOpenAI
from pinecone import Pinecone

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ProductDoc:
    """Minimal product payload the pipeline needs to embed + index."""

    tenant_id: str
    sku: str
    name: str
    description: str | None
    brand: str | None
    category: str | None
    manufacturer: str | None = None
    manufacturer_part_number: str | None = None
    compatible_models: list[str] | None = None

    def to_text(self) -> str:
        parts: list[str] = [self.name or self.sku]
        if self.brand:
            parts.append(f"Brand: {self.brand}")
        if self.manufacturer and self.manufacturer != self.brand:
            parts.append(f"Manufacturer: {self.manufacturer}")
        if self.manufacturer_part_number:
            parts.append(f"MPN: {self.manufacturer_part_number}")
        if self.category:
            parts.append(f"Category: {self.category}")
        if self.compatible_models:
            parts.append("Compatible: " + ", ".join(self.compatible_models))
        if self.description:
            parts.append(self.description)
        parts.append(f"SKU: {self.sku}")
        return " | ".join(parts)

    def metadata(self) -> dict[str, object]:
        meta: dict[str, object] = {
            "tenant_id": self.tenant_id,
            "sku": self.sku,
        }
        if self.brand:
            meta["brand"] = self.brand
        return meta

    def vector_id(self) -> str:
        return f"{self.tenant_id}:{self.sku}"


@dataclass(frozen=True, slots=True)
class VectorMatch:
    sku: str
    score: float
    tenant_id: str
    brand: str | None


class EmbeddingsPipeline:
    """Generates OpenAI embeddings and reads/writes Pinecone."""

    def __init__(
        self,
        *,
        openai_api_key: str,
        pinecone_api_key: str,
        pinecone_index: str,
        embedding_model: str = "text-embedding-3-small",
        embedding_dim: int = 1536,
    ) -> None:
        self.embedding_model = embedding_model
        self.embedding_dim = embedding_dim
        self._openai = AsyncOpenAI(api_key=openai_api_key)
        self._pc = Pinecone(api_key=pinecone_api_key)
        self._index = self._pc.Index(pinecone_index)

    async def embed_one(self, text: str) -> list[float]:
        response = await self._openai.embeddings.create(
            model=self.embedding_model,
            input=text,
        )
        return list(response.data[0].embedding)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = await self._openai.embeddings.create(
            model=self.embedding_model,
            input=texts,
        )
        return [list(item.embedding) for item in response.data]

    async def upsert_products(self, docs: Iterable[ProductDoc]) -> int:
        """Embed the given products and upsert into Pinecone, batching per
        tenant namespace. Returns the number of vectors written."""
        docs_by_tenant: dict[str, list[ProductDoc]] = {}
        for doc in docs:
            docs_by_tenant.setdefault(doc.tenant_id, []).append(doc)

        total_written = 0
        for tenant_id, tenant_docs in docs_by_tenant.items():
            vectors_payload: list[dict[str, object]] = []
            texts = [d.to_text() for d in tenant_docs]
            embeddings = await self.embed_batch(texts)
            for doc, vec in zip(tenant_docs, embeddings, strict=True):
                vectors_payload.append(
                    {
                        "id": doc.vector_id(),
                        "values": vec,
                        "metadata": doc.metadata(),
                    }
                )
            self._index.upsert(vectors=vectors_payload, namespace=tenant_id)
            total_written += len(vectors_payload)
            logger.info(
                "upserted %d vectors into Pinecone namespace=%s",
                len(vectors_payload),
                tenant_id,
            )
        return total_written

    async def query(
        self,
        *,
        tenant_id: str,
        query_text: str,
        top_k: int = 5,
        brand: str | None = None,
    ) -> list[VectorMatch]:
        """Embed ``query_text`` and ANN-search Pinecone for the given tenant."""
        vector = await self.embed_one(query_text)
        meta_filter: dict[str, object] = {"tenant_id": tenant_id}
        if brand:
            meta_filter["brand"] = brand
        result = self._index.query(
            vector=vector,
            top_k=top_k,
            namespace=tenant_id,
            include_metadata=True,
            filter=meta_filter,
        )
        matches: list[VectorMatch] = []
        for m in result.get("matches", []) or []:
            md = m.get("metadata") or {}
            matches.append(
                VectorMatch(
                    sku=str(md.get("sku") or m.get("id", "").split(":", 1)[-1]),
                    score=float(m.get("score") or 0.0),
                    tenant_id=str(md.get("tenant_id") or tenant_id),
                    brand=(str(md["brand"]) if md.get("brand") else None),
                )
            )
        return matches

    async def delete_tenant(self, tenant_id: str) -> None:
        """Remove every vector for a tenant — used when seeding from scratch."""
        try:
            self._index.delete(delete_all=True, namespace=tenant_id)
        except Exception as exc:  # noqa: BLE001
            # Pinecone raises a 404 when the namespace doesn't exist yet.
            logger.info("namespace %s delete_all skipped: %s", tenant_id, exc)


@lru_cache(maxsize=1)
def get_embeddings_pipeline() -> EmbeddingsPipeline:
    return EmbeddingsPipeline(
        openai_api_key=settings.openai_api_key,
        pinecone_api_key=settings.pinecone_api_key,
        pinecone_index=settings.pinecone_index,
        embedding_model=settings.openai_embedding_model,
        embedding_dim=settings.openai_embedding_dim,
    )
