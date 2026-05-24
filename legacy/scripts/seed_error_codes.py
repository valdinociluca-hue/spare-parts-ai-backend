"""
scripts/seed_error_codes.py — Seed the error_codes table.

Idempotent: upserts on (brand, model_pattern, error_code).

Run (Windows / PowerShell):
    python -m scripts.seed_error_codes

Brand names are stored in the normalised form used across the catalogue
(RATIONAL, UNOX, NUOVA_SIMONELLI) — the decode_error_code tool compares
brands case-insensitively with spaces squashed to underscores.
"""

import asyncio
import logging

from sqlalchemy import select

from app.db.models import ErrorCode
from app.db.session import AsyncSessionLocal, create_tables

logger = logging.getLogger(__name__)

ERROR_CODES: list[dict] = [
    # ── RATIONAL ──────────────────────────────────────────────
    {"brand": "RATIONAL", "error_code": "E5", "model_pattern": "SCC*",
     "description": "Ошибка датчика температуры ядра (щуп)",
     "likely_parts": ["5061618", "3356145"],
     "severity": "HIGH",
     "solution": "Проверить датчик ядра и кабель подключения. Заменить датчик при обрыве/КЗ."},
    {"brand": "RATIONAL", "error_code": "E10", "model_pattern": "SCC*",
     "description": "Ошибка бойлера — нет давления пара",
     "likely_parts": ["3024020", "3120405", "2102059"],
     "severity": "CRITICAL",
     "solution": "Проверить клапаны подачи воды, известковый осадок в бойлере, ТЭН бойлера."},
    {"brand": "RATIONAL", "error_code": "E20", "model_pattern": "SCC*",
     "description": "Ошибка зажигания газовой горелки",
     "likely_parts": ["3024020"],
     "severity": "HIGH",
     "solution": "Проверить блок розжига, газовый клапан и электрод ионизации."},
    {"brand": "RATIONAL", "error_code": "E31", "model_pattern": "*",
     "description": "Ошибка платы управления / связи с дисплеем",
     "likely_parts": [],
     "severity": "HIGH",
     "solution": "Проверить шлейф дисплея. При повторении — замена платы управления."},

    # ── UNOX ──────────────────────────────────────────────────
    {"brand": "UNOX", "error_code": "F3", "model_pattern": "XEFT*",
     "description": "Ошибка вентилятора (мотор/крыльчатка)",
     "likely_parts": ["5061618"],
     "severity": "MEDIUM",
     "solution": "Проверить мотор вентилятора и крыльчатку, заклинивание подшипника."},
    {"brand": "UNOX", "error_code": "E1", "model_pattern": "XEBA*",
     "description": "Перегрев камеры — сработал защитный термостат",
     "likely_parts": [],
     "severity": "HIGH",
     "solution": "Проверить термостат безопасности и датчик камеры, очистить вентиляцию."},

    # ── NUOVA SIMONELLI ───────────────────────────────────────
    {"brand": "NUOVA_SIMONELLI", "error_code": "E01", "model_pattern": "Appia*",
     "description": "Нет давления в бойлере / не набирается вода",
     "likely_parts": ["1122735", "1486051"],
     "severity": "HIGH",
     "solution": "Проверить насос ULKA, реле уровня и уплотнители группы."},
    {"brand": "NUOVA_SIMONELLI", "error_code": "E03", "model_pattern": "Aurelia*",
     "description": "Ошибка дозатора (флоуметр)",
     "likely_parts": ["1122735"],
     "severity": "MEDIUM",
     "solution": "Проверить флоуметр и его проводку, при засоре — промыть/заменить."},
]


async def seed() -> None:
    logging.basicConfig(level=logging.INFO)
    await create_tables()

    inserted = updated = 0
    async with AsyncSessionLocal() as session:
        for ec in ERROR_CODES:
            stmt = select(ErrorCode).where(
                ErrorCode.brand == ec["brand"],
                ErrorCode.model_pattern == ec["model_pattern"],
                ErrorCode.error_code == ec["error_code"],
            )
            existing = (await session.execute(stmt)).scalar_one_or_none()
            if existing:
                existing.description  = ec["description"]
                existing.likely_parts = ec["likely_parts"]
                existing.severity     = ec["severity"]
                existing.solution     = ec["solution"]
                updated += 1
            else:
                session.add(ErrorCode(**ec))
                inserted += 1
        await session.commit()

    logger.info("Error codes seeded: %d inserted, %d updated", inserted, updated)
    print(f"Done: {inserted} inserted, {updated} updated")


if __name__ == "__main__":
    asyncio.run(seed())
