"""
app/api/routes/health.py — Health and readiness endpoints.
"""

import sqlalchemy
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.db.session import get_session

router = APIRouter(prefix="/health", tags=["infra"])


@router.get("")
async def health(db: AsyncSession = Depends(get_session)):
    db_ok = False
    try:
        await db.execute(sqlalchemy.text("SELECT 1"))
        db_ok = True
    except Exception:
        pass
    return {
        "status":       "ok" if db_ok else "degraded",
        "version":      settings.app_version,
        "environment":  settings.environment,
        "llm_provider": settings.llm_provider,
        "db_connected": db_ok,
    }
