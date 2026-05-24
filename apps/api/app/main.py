from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.session import lifespan_db
from app.routers import chat, health, orders, parts, tenants

logging.basicConfig(level=settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with lifespan_db(app):
        yield


app = FastAPI(
    title="PartsAI API",
    version="0.1.0",
    description="Multi-tenant AI backend for spare-parts distributors.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(tenants.router, prefix="/api/v1")
app.include_router(parts.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(orders.router, prefix="/api/v1")
