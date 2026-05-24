"""
app/ingestion/catalog_importer.py — Import spare parts from 1C/ERP exports.

Supported formats:
  - CSV (any column mapping via config)
  - Excel (.xlsx)
  - 1C CommerceML 2.x XML (standard 1C export format)

Usage:
  python -m app.ingestion.catalog_importer --file catalog.xml --format 1c
  python -m app.ingestion.catalog_importer --file parts.xlsx --format excel
"""

import asyncio
import csv
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterator

import openpyxl

from app.config.settings import settings
from app.db.session import AsyncSessionLocal
from app.db.models import Brand, SparePart
from app.rag.embedder import embed_batch
from sqlalchemy import select

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Common part record (intermediate representation)
# ─────────────────────────────────────────────────────────────────────────────

class RawPart:
    __slots__ = ("sku", "name", "description", "brand_name", "model_codes",
                 "category", "price", "stock_qty", "metadata")

    def __init__(self, sku, name, description="", brand_name="", model_codes=None,
                 category="", price=None, stock_qty=0, metadata=None):
        self.sku         = sku.strip()
        self.name        = name.strip()
        self.description = (description or "").strip()
        self.brand_name  = (brand_name or "").strip()
        self.model_codes = model_codes or []
        self.category    = (category or "").strip()
        self.price       = price
        self.stock_qty   = stock_qty or 0
        self.metadata    = metadata or {}


# ─────────────────────────────────────────────────────────────────────────────
# Parsers
# ─────────────────────────────────────────────────────────────────────────────

def parse_csv(path: Path, delimiter=",") -> Iterator[RawPart]:
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        for row in reader:
            sku = row.get("sku") or row.get("article") or row.get("артикул") or ""
            if not sku:
                continue
            yield RawPart(
                sku=sku,
                name=row.get("name") or row.get("название") or sku,
                description=row.get("description") or row.get("описание") or "",
                brand_name=row.get("brand") or row.get("бренд") or "",
                category=row.get("category") or row.get("категория") or "",
                price=_parse_price(row.get("price") or row.get("цена")),
                stock_qty=int(row.get("stock") or row.get("остаток") or 0),
            )


def parse_excel(path: Path) -> Iterator[RawPart]:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows = ws.iter_rows(values_only=True)
    headers = [str(h).lower().strip() if h else "" for h in next(rows)]

    def col(row, *names):
        for name in names:
            if name in headers:
                v = row[headers.index(name)]
                return str(v).strip() if v is not None else ""
        return ""

    for row in rows:
        sku = col(row, "sku", "article", "артикул", "код")
        if not sku:
            continue
        yield RawPart(
            sku=sku,
            name=col(row, "name", "название", "наименование") or sku,
            description=col(row, "description", "описание"),
            brand_name=col(row, "brand", "бренд", "производитель"),
            category=col(row, "category", "категория"),
            price=_parse_price(col(row, "price", "цена")),
            stock_qty=int(col(row, "stock", "остаток") or 0),
        )


def parse_1c_xml(path: Path) -> Iterator[RawPart]:
    """
    Parse 1C CommerceML 2.x XML export.
    Handles both catalog (Каталог) and offers (Предложения) sections.
    """
    ns = {"cm": "urn:1C.ru:commerceml_2"}
    tree = ET.parse(path)
    root = tree.getroot()

    # Try standard CommerceML namespace, fall back to no-namespace
    def find_all(node, tag):
        result = node.findall(f"cm:{tag}", ns)
        if not result:
            result = node.findall(tag)
        return result

    def find_text(node, tag, default=""):
        el = node.find(f"cm:{tag}", ns) or node.find(tag)
        return (el.text or "").strip() if el is not None else default

    # Build price map from Offers section
    price_map: dict[str, float] = {}
    for offer in root.iter("{urn:1C.ru:commerceml_2}Предложение") or root.iter("Предложение"):
        pid  = find_text(offer, "Ид")
        pval = find_text(offer, "Цена")
        if pid and pval:
            price_map[pid] = _parse_price(pval) or 0.0

    # Parse products from Catalog section
    for product in root.iter("{urn:1C.ru:commerceml_2}Товар") or root.iter("Товар"):
        sku  = find_text(product, "Ид") or find_text(product, "Артикул")
        name = find_text(product, "Наименование")
        if not sku or not name:
            continue

        desc      = find_text(product, "Описание")
        group     = find_text(product, "Группа") or find_text(product, "ГруппыТоваров")
        brand     = ""
        model_codes: list[str] = []

        # Extract brand/model from properties (РеквизитыТовара / ЗначенияРеквизитов)
        for prop in product.iter("{urn:1C.ru:commerceml_2}ЗначениеРеквизита") or product.iter("ЗначениеРеквизита"):
            pname = find_text(prop, "Наименование").lower()
            pval  = find_text(prop, "Значение")
            if "бренд" in pname or "производитель" in pname:
                brand = pval
            elif "модель" in pname:
                model_codes.append(pval)

        yield RawPart(
            sku=sku,
            name=name,
            description=desc,
            brand_name=brand,
            model_codes=model_codes,
            category=group,
            price=price_map.get(sku),
            metadata={"source": "1c_export", "1c_group": group},
        )


# ─────────────────────────────────────────────────────────────────────────────
# DB upsert with embedding
# ─────────────────────────────────────────────────────────────────────────────

async def import_parts(parts: list[RawPart], batch_size: int = 50) -> dict:
    """Upsert parts into spare_parts table, compute embeddings in batches."""
    stats = {"inserted": 0, "updated": 0, "skipped": 0}

    async with AsyncSessionLocal() as session:
        # Build brand cache
        brand_ids: dict[str, str] = {}

        async def get_or_create_brand(name: str) -> str | None:
            if not name:
                return None
            slug = name.lower().replace(" ", "-").replace("/", "-")[:50]
            if slug in brand_ids:
                return brand_ids[slug]
            existing = (await session.execute(
                select(Brand).where(Brand.slug == slug)
            )).scalar_one_or_none()
            if existing:
                brand_ids[slug] = existing.id
                return existing.id
            brand = Brand(name=name, slug=slug)
            session.add(brand)
            await session.flush()
            brand_ids[slug] = brand.id
            return brand.id

        # Process in batches for embedding efficiency
        for i in range(0, len(parts), batch_size):
            batch = parts[i : i + batch_size]
            texts = [f"{p.name} {p.description}" for p in batch]
            embeddings = embed_batch(texts)

            for part, emb in zip(batch, embeddings):
                if not part.sku:
                    stats["skipped"] += 1
                    continue

                brand_id = await get_or_create_brand(part.brand_name)
                existing = await session.get(SparePart, part.sku)

                if existing:
                    existing.name                  = part.name
                    existing.description           = part.description
                    existing.brand_id              = brand_id
                    existing.compatible_models     = part.model_codes
                    existing.category              = part.category
                    existing.price                 = part.price
                    existing.stock_qty             = part.stock_qty
                    existing.embedding             = emb
                    existing.metadata_             = part.metadata
                    stats["updated"] += 1
                else:
                    session.add(SparePart(
                        sku=part.sku,
                        name=part.name,
                        description=part.description,
                        brand_id=brand_id,
                        compatible_models=part.model_codes,
                        category=part.category,
                        price=part.price,
                        stock_qty=part.stock_qty,
                        embedding=emb,
                        metadata_=part.metadata,
                    ))
                    stats["inserted"] += 1

            await session.commit()
            logger.info("Batch %d-%d committed (%s)", i, i + len(batch), stats)

    return stats


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def _parse_price(value) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).replace(",", ".").replace(" ", "").strip())
    except ValueError:
        return None


async def _main():
    import argparse
    parser = argparse.ArgumentParser(description="Import spare parts catalog")
    parser.add_argument("--file",   required=True, help="Path to catalog file")
    parser.add_argument("--format", choices=["csv", "excel", "1c"], default="csv")
    parser.add_argument("--delimiter", default=",", help="CSV delimiter")
    args = parser.parse_args()

    path = Path(args.file)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if args.format == "csv":
        parts = list(parse_csv(path, delimiter=args.delimiter))
    elif args.format == "excel":
        parts = list(parse_excel(path))
    else:
        parts = list(parse_1c_xml(path))

    logger.info("Parsed %d parts from %s", len(parts), path.name)
    stats = await import_parts(parts)
    print(f"Done: {stats}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_main())
