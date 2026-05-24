"""
app/ingestion/website_scraper.py — Crawl lvtrade.ru and ingest content into document_chunks.

Strategy:
  1. Crawl sitemap.xml or recursively follow links from base URL
  2. For each page: extract title + main content text (strip nav/footer/ads)
  3. Chunk text into ~500-token segments with overlap
  4. Embed each chunk and upsert into document_chunks

Usage:
  python -m app.ingestion.website_scraper --url https://lvtrade.ru --max-pages 500
"""

import asyncio
import logging
import re
from typing import Iterator
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.config.settings import settings

logger = logging.getLogger(__name__)

CHUNK_SIZE    = 500    # characters per chunk
CHUNK_OVERLAP = 100    # overlap between consecutive chunks
_STRIP_TAGS   = {"script", "style", "nav", "footer", "header", "aside", "form"}


# ─────────────────────────────────────────────────────────────────────────────
# Crawler
# ─────────────────────────────────────────────────────────────────────────────

class PageData:
    __slots__ = ("url", "title", "text", "model_hint")

    def __init__(self, url, title, text, model_hint=""):
        self.url         = url
        self.title       = title
        self.text        = text
        self.model_hint  = model_hint   # extracted from URL if applicable


async def crawl(base_url: str, max_pages: int = 500) -> list[PageData]:
    """
    BFS crawl from base_url. Stays within the same domain.
    Returns list of PageData objects with extracted text.
    """
    domain  = urlparse(base_url).netloc
    visited: set[str] = set()
    queue   = [base_url]
    results = []

    async with httpx.AsyncClient(timeout=15, follow_redirects=True,
                                  headers={"User-Agent": "LVTrade-Bot/1.0"}) as client:
        while queue and len(results) < max_pages:
            url = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)

            try:
                resp = await client.get(url)
                if resp.status_code != 200:
                    continue
                if "text/html" not in resp.headers.get("content-type", ""):
                    continue
            except Exception as e:
                logger.debug("Fetch error %s: %s", url, e)
                continue

            page = _parse_page(url, resp.text)
            if page and len(page.text) > 100:
                results.append(page)
                logger.info("[%d/%d] %s", len(results), max_pages, url)

            # Discover links
            soup = BeautifulSoup(resp.text, "lxml")
            for a in soup.find_all("a", href=True):
                href = urljoin(url, a["href"])
                parsed = urlparse(href)
                if parsed.netloc == domain and href not in visited:
                    # Skip non-content pages
                    if not re.search(r"\.(pdf|jpg|png|zip|doc|xls)$", parsed.path, re.I):
                        queue.append(href)

    logger.info("Crawl complete: %d pages from %s", len(results), base_url)
    return results


def _parse_page(url: str, html: str) -> PageData | None:
    soup = BeautifulSoup(html, "lxml")

    # Remove noise elements
    for tag in soup.find_all(_STRIP_TAGS):
        tag.decompose()

    title = (soup.title.string or "").strip() if soup.title else ""

    # Try to find main content block
    main = (
        soup.find("main")
        or soup.find("article")
        or soup.find(id=re.compile(r"content|main|product", re.I))
        or soup.find(class_=re.compile(r"content|main|product", re.I))
        or soup.body
    )
    if main is None:
        return None

    text = re.sub(r"\s+", " ", main.get_text(separator=" ")).strip()
    if not text:
        return None

    # Extract model hint from URL (e.g. /products/electrolux-erc3711/ → erc3711)
    model_hint = ""
    path_parts = urlparse(url).path.strip("/").split("/")
    if len(path_parts) >= 2:
        model_hint = path_parts[-1]

    return PageData(url=url, title=title, text=text, model_hint=model_hint)


# ─────────────────────────────────────────────────────────────────────────────
# Chunker
# ─────────────────────────────────────────────────────────────────────────────

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks by word boundaries."""
    words  = text.split()
    chunks = []
    start  = 0

    while start < len(words):
        end   = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start = end - overlap
        if start >= len(words):
            break

    return chunks


# ─────────────────────────────────────────────────────────────────────────────
# DB ingest
# ─────────────────────────────────────────────────────────────────────────────

async def ingest_pages(pages: list[PageData]) -> dict:
    from app.db.session import AsyncSessionLocal
    from app.db.models import DocumentChunk, DocumentSource
    from app.rag.embedder import embed_batch

    stats = {"sources": 0, "chunks": 0}

    async with AsyncSessionLocal() as session:
        for page in pages:
            # Create document source
            source = DocumentSource(
                source_type="website",
                source_url=page.url,
                title=page.title,
            )
            session.add(source)
            await session.flush()

            chunks  = chunk_text(page.text)
            if not chunks:
                continue

            vectors = embed_batch(chunks)

            for idx, (text, vec) in enumerate(zip(chunks, vectors)):
                session.add(DocumentChunk(
                    source_id=source.id,
                    content=text,
                    chunk_index=idx,
                    section_type="website",
                    embedding=vec,
                    metadata_={"url": page.url, "model_hint": page.model_hint},
                ))

            await session.commit()
            stats["sources"] += 1
            stats["chunks"]  += len(chunks)
            logger.debug("Ingested %s (%d chunks)", page.url, len(chunks))

    return stats


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

async def _main():
    import argparse
    parser = argparse.ArgumentParser(description="Scrape and ingest website content")
    parser.add_argument("--url",       default=settings.website_base_url)
    parser.add_argument("--max-pages", type=int, default=500)
    args = parser.parse_args()

    pages = await crawl(args.url, max_pages=args.max_pages)
    stats = await ingest_pages(pages)
    print(f"Done: {stats}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_main())
