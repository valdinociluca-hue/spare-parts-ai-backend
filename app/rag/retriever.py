"""
app/rag/retriever.py — Vector similarity retrieval for RAG.

Retrieves relevant documents from the vector store given a query.
Used by agents to ground LLM responses in actual catalogue data.

Why RAG for this system:
  - The spare parts catalogue is too large to fit in a prompt
  - Part numbers, compatibility, and specifications must be accurate
  - The LLM must never hallucinate catalogue data
  - RAG retrieves the relevant slice of the catalogue per request

Components (all TODO):
  retriever.retrieve(query, top_k=5) -> list[Document]
    - Embeds the query using an embedding model
    - Queries the vector store for nearest neighbours
    - Returns Document objects with content + metadata

Planned vector store options:
  - pgvector (PostgreSQL extension) — preferred for minimal infra
  - Qdrant — if dedicated vector DB is needed at scale
  - Weaviate — alternative option

Implementation notes (TODO):
  - Implement retrieve(query: str, top_k: int) -> list[Document]
  - Use app/rag/embedder.py for query embedding
  - Use app/rag/vector_store.py for similarity search
  - Add metadata filters (equipment brand, equipment type)
"""


class Retriever:
    async def retrieve(self, query: str, top_k: int = 5) -> list:
        """Retrieve top-k relevant documents for a given query."""
        # TODO: embed query, query vector store, return Document list
        raise NotImplementedError
