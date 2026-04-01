"""
app/main.py — FastAPI application entry point.
"""

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import chat, health, webhooks
from app.config.logging import configure_logging
from app.config.settings import settings
from app.db.session import create_tables

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s v%s [%s | LLM: %s]",
                settings.app_name, settings.app_version,
                settings.environment, settings.llm_provider)
    await create_tables()
    logger.info("Database ready")
    # Eager-import tools so they self-register on the tool_registry singleton
    import app.tools.catalog_search   # noqa: F401
    import app.tools.document_search  # noqa: F401
    import app.tools.escalation       # noqa: F401
    yield
    logger.info("Shutting down")


app = FastAPI(
    title       = "Spare Parts AI Backend",
    version     = settings.app_version,
    lifespan    = lifespan,
    docs_url    = "/docs"  if not settings.is_production else None,
    redoc_url   = "/redoc" if not settings.is_production else None,
)

_origins = settings.allowed_origins if settings.is_production else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins     = _origins,
    allow_credentials = True,
    allow_methods     = ["GET", "POST", "OPTIONS"],
    allow_headers     = ["*"],
)

app.include_router(health.router,   prefix="/api/v1")
app.include_router(webhooks.router, prefix="/api/v1")
app.include_router(chat.router,     prefix="/api/v1")


@app.get("/", include_in_schema=False)
async def root():
    return {"service": settings.app_name, "version": settings.app_version}


@app.exception_handler(Exception)
async def _unhandled(request: Request, exc: Exception):
    eid = str(uuid.uuid4())[:8]
    logger.exception("Unhandled [%s]: %s", eid, exc)
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": "Internal server error", "error_id": eid},
    )
