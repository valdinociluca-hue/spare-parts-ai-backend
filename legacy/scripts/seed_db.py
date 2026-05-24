"""
scripts/seed_db.py — Development database seeder.

Seeds a small but realistic catalogue (including the key test SKUs) so the
chat path and catalogue endpoints are exercisable before the real Excel
exports are imported. Idempotent: upserts on SKU.

NOT for production. Run (Windows / PowerShell):
    python -m scripts.seed_db

After seeding, also run:
    python -m scripts.seed_error_codes
"""

import asyncio
import logging

from sqlalchemy import select

from app.db.models import Brand, SparePart
from app.db.session import AsyncSessionLocal, create_tables
from app.rag.embedder import embed_batch

logger = logging.getLogger(__name__)

# (sku, name, description, brand, category, price, stock, compatible_models)
PARTS: list[tuple] = [
    ("1122735", "Насос вибрационный ULKA EX5 48W",
     "Вибрационный насос ULKA EX5 48 Вт для кофемашин. Подаёт воду в бойлер. "
     "Симптомы отказа: нет подачи воды, кофемашина не набирает давление, гудит без воды.",
     "NUOVA SIMONELLI", "PUMP", 3200, 14, ["Appia", "Appia II", "Aurelia", "Oscar"]),

    ("5061618", "Мотор вентилятора конвекции Rational SCC",
     "Двигатель вентилятора циркуляции воздуха для пароконвектоматов Rational. "
     "Симптомы: неравномерная пропечка, шум, ошибка вентилятора, не вращается крыльчатка.",
     "RATIONAL", "MOTOR", 28500, 3, ["SCC 61", "SCC 101", "SCC 102", "SCC WE 61"]),

    ("3356145", "Кран шаровый сливной Rational SCC",
     "Шаровый кран системы слива/CleanJet для пароконвектоматов Rational. "
     "Симптомы: не сливается вода, течь под аппаратом, ошибка слива.",
     "RATIONAL", "VALVE", 9800, 7, ["SCC 61", "SCC 101", "SCC WE 101"]),

    ("1486051", "Уплотнитель группы Nuova Simonelli 8.5мм",
     "Уплотнительное кольцо (прокладка) заварочной группы кофемашины, 8.5 мм. "
     "Симптомы: течь из группы, падение давления, кофе проливается мимо.",
     "NUOVA SIMONELLI", "SEAL", 280, 120, ["Appia", "Appia II", "Aurelia"]),

    ("3024020", "Клапан подачи воды Rational (соленоид)",
     "Электромагнитный клапан подачи воды в бойлер пароконвектомата Rational. "
     "Симптомы: нет пара, не набирается вода в бойлер, ошибка бойлера.",
     "RATIONAL", "VALVE", 7400, 9, ["SCC 61", "SCC 101", "SCC 201"]),

    ("3120405", "ТЭН бойлера Rational SCC 9 кВт",
     "Нагревательный элемент бойлера парогенератора Rational, 9 кВт. "
     "Симптомы: нет пара, слабый пар, долгий нагрев, ошибка бойлера.",
     "RATIONAL", "HEATING", 41000, 2, ["SCC 61", "SCC 101"]),

    ("2102059", "Датчик уровня воды бойлера Rational",
     "Электрод/датчик уровня воды в бойлере пароконвектомата Rational. "
     "Симптомы: перелив, нет пара, ошибка давления пара.",
     "RATIONAL", "SENSOR", 5600, 11, ["SCC 61", "SCC 101", "SCC WE 61"]),
]


async def seed() -> None:
    logging.basicConfig(level=logging.INFO)
    await create_tables()

    texts = [f"{p[1]} {p[2]}" for p in PARTS]
    logger.info("Embedding %d catalogue rows…", len(texts))
    embeddings = embed_batch(texts)

    inserted = updated = 0
    async with AsyncSessionLocal() as session:
        brand_cache: dict[str, str] = {}

        async def get_brand(name: str) -> str:
            slug = name.lower().replace(" ", "-")
            if slug in brand_cache:
                return brand_cache[slug]
            existing = (await session.execute(
                select(Brand).where(Brand.slug == slug)
            )).scalar_one_or_none()
            if existing:
                brand_cache[slug] = existing.id
                return existing.id
            b = Brand(name=name, slug=slug)
            session.add(b)
            await session.flush()
            brand_cache[slug] = b.id
            return b.id

        for (sku, name, desc, brand, cat, price, stock, models), emb in zip(PARTS, embeddings):
            brand_id = await get_brand(brand)
            existing = await session.get(SparePart, sku)
            if existing:
                existing.name              = name
                existing.description       = desc
                existing.brand_id          = brand_id
                existing.category          = cat
                existing.price             = price
                existing.stock_qty         = stock
                existing.compatible_models = models
                existing.embedding         = emb
                updated += 1
            else:
                session.add(SparePart(
                    sku=sku, name=name, description=desc, brand_id=brand_id,
                    category=cat, price=price, stock_qty=stock,
                    compatible_models=models, embedding=emb,
                ))
                inserted += 1
        await session.commit()

    logger.info("Catalogue seeded: %d inserted, %d updated", inserted, updated)
    print(f"Done: {inserted} inserted, {updated} updated")


if __name__ == "__main__":
    asyncio.run(seed())
