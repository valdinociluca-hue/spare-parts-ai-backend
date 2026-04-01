"""
app/rag/embedder.py — Text embedding for vector search.

Converts text (queries and documents) into dense vector representations
for similarity search.

Used by:
  - retriever.py (query embedding at inference time)
  - scripts/embed_catalogue.py (document embedding at index time)

Embedding model options (TODO: choose one):
  - OpenAI text-embedding-3-small  (fast, cheap, hosted)
  - OpenAI text-embedding-3-large  (higher quality)
  - sentence-transformers/all-MiniLM-L6-v2 (local, no API cost)
  - E5-large (strong multilingual, good for Russian)

Design: the embedder is a swappable component. Changing the model
requires re-embedding the entire catalogue (scripts/embed_catalogue.py).

TODO:
  - Implement embed(text: str) -> list[float]
  - Implement embed_batch(texts: list[str]) -> list[list[float]]
  - Add caching for repeated queries (Redis or in-memory LRU)
  - Expose the embedding dimension for vector store schema setup
"""


class Embedder:
    async def embed(self, text: str) -> list[float]:
        """Embed a single text string."""
        # TODO: call embedding API or local model, return vector
        raise NotImplementedError

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts efficiently."""
        # TODO: batch API call, return list of vectors
        raise NotImplementedError
