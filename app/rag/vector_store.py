"""
app/rag/vector_store.py — Vector store client abstraction.

Wraps the underlying vector database so the rest of the application
doesn't depend on a specific vector store implementation.

If we switch from pgvector to Qdrant, only this file changes.

Operations:
  - search(vector, top_k, filters) -> list[Document]
  - upsert(id, vector, metadata) — used during catalogue indexing
  - delete(id) — used when catalogue entries are removed

Document schema (metadata stored alongside vectors):
  - part_number    str
  - description    str
  - equipment_brand str
  - equipment_model str
  - source_file    str (for traceability)
  - chunk_index    int (if document was chunked)

TODO:
  - Choose vector store (pgvector recommended for MVP)
  - Implement search(), upsert(), delete()
  - Add metadata filtering (filter by equipment brand/model)
  - Add connection pooling and health check
"""


class VectorStore:
    async def search(self, vector: list[float], top_k: int = 5, filters: dict = None) -> list:
        """Find top-k nearest vectors with optional metadata filters."""
        # TODO: execute similarity query, return Document list
        raise NotImplementedError

    async def upsert(self, doc_id: str, vector: list[float], metadata: dict) -> None:
        """Insert or update a document in the vector store."""
        # TODO: implement upsert operation
        raise NotImplementedError
