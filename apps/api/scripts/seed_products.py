"""Seed 20 mock spare-parts products (10 per tenant) and index them.

Run from the repo root:

    DYLD_LIBRARY_PATH=/opt/homebrew/opt/expat/lib \
        apps/api/.venv/bin/python -m scripts.seed_products

Idempotent: products are upserted by (tenant_id, sku); Pinecone namespaces
are cleared before upserting so re-running gives a clean state.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import asyncpg

# Allow running as `python apps/api/scripts/seed_products.py`.
APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

# Load .env (repo root)
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


# Each product: (sku, name, description, brand, manufacturer, mpn, category, compatible, qty, price, currency)
LV_TRADE_PRODUCTS: list[dict] = [
    {
        "sku": "LV-RAT-3024.0301",
        "name": "Насос дренажный для пароконвектомата Rational SCC",
        "description": "Оригинальный дренажный насос для пароконвектоматов Rational SelfCookingCenter. Удаляет конденсат и отработанную воду. 230В, 50 Гц.",
        "brand": "Rational",
        "manufacturer": "Rational AG",
        "mpn": "3024.0301",
        "category": "Насосы",
        "compatible": ["SCC 61", "SCC 101", "SCC 201", "iCombi Pro 6-1/1", "iCombi Pro 10-1/1"],
        "qty": 8.0, "price": 24500, "currency": "RUB",
    },
    {
        "sku": "LV-RAT-40.00.115",
        "name": "Уплотнитель двери Rational iCombi Pro 6-1/1",
        "description": "Силиконовое уплотнение двери для пароконвектоматов iCombi Pro / SelfCookingCenter 6-1/1. Термостойкое, пищевой силикон.",
        "brand": "Rational",
        "manufacturer": "Rational AG",
        "mpn": "40.00.115",
        "category": "Уплотнители",
        "compatible": ["iCombi Pro 6-1/1", "SCC 61"],
        "qty": 12.0, "price": 6800, "currency": "RUB",
    },
    {
        "sku": "LV-RAT-87.00.452",
        "name": "Датчик температуры (термопара) Rational",
        "description": "Сменный термодатчик (термопара типа K) для пароконвектоматов Rational. Контроль температуры камеры. С разъёмом.",
        "brand": "Rational",
        "manufacturer": "Rational AG",
        "mpn": "87.00.452",
        "category": "Датчики",
        "compatible": ["SCC 61", "SCC 101", "iCombi Pro 6-1/1", "iCombi Pro 10-1/1"],
        "qty": 5.0, "price": 9900, "currency": "RUB",
    },
    {
        "sku": "LV-RAT-22.00.387P",
        "name": "ТЭН парогенератора Rational SCC 101",
        "description": "Нагревательный элемент парогенератора 9 кВт для Rational SCC / iCombi 10-1/1. 400В трёхфазный.",
        "brand": "Rational",
        "manufacturer": "Rational AG",
        "mpn": "22.00.387P",
        "category": "ТЭНы",
        "compatible": ["SCC 101", "iCombi Pro 10-1/1"],
        "qty": 3.0, "price": 32000, "currency": "RUB",
    },
    {
        "sku": "LV-UNX-KCH1018A",
        "name": "Вентилятор камеры пароконвектомата Unox ChefTop",
        "description": "Двигатель вентилятора камеры для печей Unox ChefTop XEVC. Реверсивный, с лопастью. Для моделей серии Mind.Maps.",
        "brand": "Unox",
        "manufacturer": "Unox S.p.A.",
        "mpn": "KCH1018A",
        "category": "Вентиляторы",
        "compatible": ["XEVC-0511-EPR", "XEVC-1011-EPR", "ChefTop MIND.Maps"],
        "qty": 6.0, "price": 18900, "currency": "RUB",
    },
    {
        "sku": "LV-UNX-KVT1075A",
        "name": "Плата управления Unox XEFT-10EU-ELDP",
        "description": "Электронная плата управления для печи Unox BakerTop. С дисплеем. Версия с прошивкой Mind.Maps.",
        "brand": "Unox",
        "manufacturer": "Unox S.p.A.",
        "mpn": "KVT1075A",
        "category": "Электроника",
        "compatible": ["XEFT-10EU-ELDP", "BakerTop MIND.Maps"],
        "qty": 2.0, "price": 67000, "currency": "RUB",
    },
    {
        "sku": "LV-UNX-VC1015A0",
        "name": "Соленоидный клапан подачи воды Unox",
        "description": "Клапан подачи воды (электромагнитный) для пароконвектоматов Unox XEVC / XEFT. 230В.",
        "brand": "Unox",
        "manufacturer": "Unox S.p.A.",
        "mpn": "VC1015A0",
        "category": "Клапаны",
        "compatible": ["XEVC-0511", "XEVC-1011", "XEFT-10EU"],
        "qty": 14.0, "price": 4200, "currency": "RUB",
    },
    {
        "sku": "LV-NSI-08800217",
        "name": "Группа заварная (поршень) Nuova Simonelli Aurelia",
        "description": "Заварной узел для профессиональных эспрессо-машин Nuova Simonelli Aurelia II. Включает поршень и уплотнения.",
        "brand": "Nuova Simonelli",
        "manufacturer": "Nuova Simonelli S.p.A.",
        "mpn": "08800217",
        "category": "Группы",
        "compatible": ["Aurelia II", "Aurelia Wave"],
        "qty": 4.0, "price": 38900, "currency": "RUB",
    },
    {
        "sku": "LV-NSI-04000067",
        "name": "Сито двойное 14г Nuova Simonelli 58мм",
        "description": "Двойное сито (фильтр) для портафильтра 58 мм. Обжарка 14 г. Совместимо с большинством эспрессо-машин Nuova Simonelli.",
        "brand": "Nuova Simonelli",
        "manufacturer": "Nuova Simonelli S.p.A.",
        "mpn": "04000067",
        "category": "Фильтры",
        "compatible": ["Aurelia II", "Appia II", "Musica"],
        "qty": 25.0, "price": 1200, "currency": "RUB",
    },
    {
        "sku": "LV-NSI-02100170",
        "name": "Помпа вибрационная 230В Nuova Simonelli Musica",
        "description": "Вибрационная помпа Ulka EP5 для эспрессо-машины Nuova Simonelli Musica. Давление до 15 бар.",
        "brand": "Nuova Simonelli",
        "manufacturer": "Nuova Simonelli S.p.A.",
        "mpn": "02100170",
        "category": "Помпы",
        "compatible": ["Musica"],
        "qty": 7.0, "price": 5400, "currency": "RUB",
    },
]


EQUIPART_PRODUCTS: list[dict] = [
    {
        "sku": "EQ-RAT-3024.0301",
        "name": "Drain pump for Rational SCC / iCombi Pro combi steamer",
        "description": "Original drain pump for Rational SelfCookingCenter and iCombi Pro combi ovens. Removes condensate and waste water. 230V, 50Hz.",
        "brand": "Rational",
        "manufacturer": "Rational AG",
        "mpn": "3024.0301",
        "category": "Pumps",
        "compatible": ["SCC 61", "SCC 101", "iCombi Pro 6-1/1", "iCombi Pro 10-1/1"],
        "qty": 10.0, "price": 289.00, "currency": "EUR",
    },
    {
        "sku": "EQ-RAT-40.00.115",
        "name": "Door gasket / seal for Rational iCombi Pro 6-1/1",
        "description": "Food-grade silicone door seal for Rational iCombi Pro and SelfCookingCenter 6-1/1 combi ovens. Heat resistant.",
        "brand": "Rational",
        "manufacturer": "Rational AG",
        "mpn": "40.00.115",
        "category": "Gaskets",
        "compatible": ["iCombi Pro 6-1/1", "SCC 61"],
        "qty": 18.0, "price": 79.50, "currency": "EUR",
    },
    {
        "sku": "EQ-RAT-87.00.452",
        "name": "Cabinet temperature probe (Type-K thermocouple) for Rational",
        "description": "Replacement cabinet temperature probe (Type-K thermocouple) for Rational combi ovens. Plug-and-play connector.",
        "brand": "Rational",
        "manufacturer": "Rational AG",
        "mpn": "87.00.452",
        "category": "Sensors",
        "compatible": ["SCC 61", "SCC 101", "iCombi Pro 6-1/1", "iCombi Pro 10-1/1"],
        "qty": 9.0, "price": 119.00, "currency": "EUR",
    },
    {
        "sku": "EQ-RAT-22.00.387P",
        "name": "Steam generator heating element 9kW for Rational SCC 101",
        "description": "Replacement 9 kW steam generator heating element for Rational SCC / iCombi Pro 10-1/1. 400V three-phase.",
        "brand": "Rational",
        "manufacturer": "Rational AG",
        "mpn": "22.00.387P",
        "category": "Heating elements",
        "compatible": ["SCC 101", "iCombi Pro 10-1/1"],
        "qty": 4.0, "price": 380.00, "currency": "EUR",
    },
    {
        "sku": "EQ-UNX-KCH1018A",
        "name": "Cavity fan motor for Unox ChefTop combi oven",
        "description": "Reversible cavity fan motor with impeller for Unox ChefTop XEVC convection-steam ovens (MIND.Maps series).",
        "brand": "Unox",
        "manufacturer": "Unox S.p.A.",
        "mpn": "KCH1018A",
        "category": "Fans",
        "compatible": ["XEVC-0511-EPR", "XEVC-1011-EPR", "ChefTop MIND.Maps"],
        "qty": 7.0, "price": 215.00, "currency": "EUR",
    },
    {
        "sku": "EQ-UNX-KVT1075A",
        "name": "Control board for Unox BakerTop XEFT-10EU-ELDP",
        "description": "Electronic control board with display for Unox BakerTop oven, MIND.Maps firmware revision.",
        "brand": "Unox",
        "manufacturer": "Unox S.p.A.",
        "mpn": "KVT1075A",
        "category": "Electronics",
        "compatible": ["XEFT-10EU-ELDP", "BakerTop MIND.Maps"],
        "qty": 2.0, "price": 760.00, "currency": "EUR",
    },
    {
        "sku": "EQ-UNX-VC1015A0",
        "name": "Water inlet solenoid valve for Unox combi ovens",
        "description": "230V electromagnetic water inlet valve for Unox XEVC and XEFT combi ovens.",
        "brand": "Unox",
        "manufacturer": "Unox S.p.A.",
        "mpn": "VC1015A0",
        "category": "Valves",
        "compatible": ["XEVC-0511", "XEVC-1011", "XEFT-10EU"],
        "qty": 22.0, "price": 48.00, "currency": "EUR",
    },
    {
        "sku": "EQ-NSI-08800217",
        "name": "Brew group / piston for Nuova Simonelli Aurelia espresso machine",
        "description": "Brew group for Nuova Simonelli Aurelia II / Aurelia Wave professional espresso machines. Piston and seals included.",
        "brand": "Nuova Simonelli",
        "manufacturer": "Nuova Simonelli S.p.A.",
        "mpn": "08800217",
        "category": "Brew groups",
        "compatible": ["Aurelia II", "Aurelia Wave"],
        "qty": 5.0, "price": 445.00, "currency": "EUR",
    },
    {
        "sku": "EQ-NSI-04000067",
        "name": "Double basket filter 14g for Nuova Simonelli 58mm portafilter",
        "description": "Double basket (filter) for 58 mm portafilter, 14g dose. Fits most Nuova Simonelli espresso machines.",
        "brand": "Nuova Simonelli",
        "manufacturer": "Nuova Simonelli S.p.A.",
        "mpn": "04000067",
        "category": "Filters",
        "compatible": ["Aurelia II", "Appia II", "Musica"],
        "qty": 35.0, "price": 14.50, "currency": "EUR",
    },
    {
        "sku": "EQ-NSI-02100170",
        "name": "Vibration pump 230V Ulka EP5 for Nuova Simonelli Musica",
        "description": "Ulka EP5 vibration pump for Nuova Simonelli Musica espresso machine. 15 bar max pressure.",
        "brand": "Nuova Simonelli",
        "manufacturer": "Nuova Simonelli S.p.A.",
        "mpn": "02100170",
        "category": "Pumps",
        "compatible": ["Musica"],
        "qty": 8.0, "price": 62.00, "currency": "EUR",
    },
]


def _normalize_dsn(dsn: str) -> str:
    return dsn.replace("postgresql+asyncpg://", "postgresql://")


async def _upsert_products(
    conn: asyncpg.Connection,
    tenant_id: str,
    products: list[dict],
) -> None:
    sql = """
        insert into public.products (
            tenant_id, sku, name, description, brand, manufacturer,
            manufacturer_part_number, category, compatible_models,
            qty_stock, price_base, currency
        )
        values ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
        on conflict (tenant_id, sku) do update set
            name        = excluded.name,
            description = excluded.description,
            brand       = excluded.brand,
            manufacturer = excluded.manufacturer,
            manufacturer_part_number = excluded.manufacturer_part_number,
            category    = excluded.category,
            compatible_models = excluded.compatible_models,
            qty_stock   = excluded.qty_stock,
            price_base  = excluded.price_base,
            currency    = excluded.currency
    """
    for p in products:
        await conn.execute(
            sql,
            tenant_id,
            p["sku"],
            p["name"],
            p["description"],
            p["brand"],
            p["manufacturer"],
            p["mpn"],
            p["category"],
            p["compatible"],
            p["qty"],
            p["price"],
            p["currency"],
        )


async def main() -> None:
    dsn = _normalize_dsn(settings.database_url)
    conn = await asyncpg.connect(dsn)
    try:
        tenants = await conn.fetch(
            "select id::text as id, slug from public.tenants where slug in ('lvtrade','equipart')"
        )
        tenant_ids = {row["slug"]: row["id"] for row in tenants}
        if "lvtrade" not in tenant_ids or "equipart" not in tenant_ids:
            raise RuntimeError(f"missing tenants — got {tenant_ids}")

        await _upsert_products(conn, tenant_ids["lvtrade"], LV_TRADE_PRODUCTS)
        await _upsert_products(conn, tenant_ids["equipart"], EQUIPART_PRODUCTS)

        counts = await conn.fetch(
            "select tenant_id::text as tenant_id, count(*) as n from public.products group by tenant_id"
        )
        print("Postgres product counts:", json.dumps([dict(r) for r in counts], indent=2))
    finally:
        await conn.close()

    pipe = EmbeddingsPipeline(
        openai_api_key=settings.openai_api_key,
        pinecone_api_key=settings.pinecone_api_key,
        pinecone_index=settings.pinecone_index,
        embedding_model=settings.openai_embedding_model,
        embedding_dim=settings.openai_embedding_dim,
    )

    for slug, products in (("lvtrade", LV_TRADE_PRODUCTS), ("equipart", EQUIPART_PRODUCTS)):
        tenant_id = tenant_ids[slug]
        await pipe.delete_tenant(tenant_id)
        docs = [
            ProductDoc(
                tenant_id=tenant_id,
                sku=p["sku"],
                name=p["name"],
                description=p["description"],
                brand=p["brand"],
                category=p["category"],
                manufacturer=p["manufacturer"],
                manufacturer_part_number=p["mpn"],
                compatible_models=p["compatible"],
            )
            for p in products
        ]
        written = await pipe.upsert_products(docs)
        print(f"{slug}: wrote {written} vectors to Pinecone (namespace={tenant_id})")


if __name__ == "__main__":
    asyncio.run(main())
