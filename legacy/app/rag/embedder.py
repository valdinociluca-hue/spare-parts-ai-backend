"""
app/rag/embedder.py — Text embedding using sentence-transformers.

Model: paraphrase-multilingual-mpnet-base-v2
  - 768 dimensions
  - Strong Russian + English support
  - ~420MB on disk, loaded once at startup via lru_cache
"""

import logging
from functools import lru_cache

from app.config.settings import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _load_model():
    from sentence_transformers import SentenceTransformer
    logger.info("Loading embedding model: %s", settings.embedding_model)
    model = SentenceTransformer(settings.embedding_model)
    logger.info("Embedding model loaded (dim=%d)", settings.vector_dim)
    return model


def embed(text: str) -> list[float]:
    """Embed a single text. Returns list[float] of length vector_dim."""
    model = _load_model()
    return model.encode(text, normalize_embeddings=True).tolist()


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed multiple texts in one forward pass."""
    if not texts:
        return []
    model = _load_model()
    vectors = model.encode(texts, normalize_embeddings=True, batch_size=32, show_progress_bar=False)
    return [v.tolist() for v in vectors]
