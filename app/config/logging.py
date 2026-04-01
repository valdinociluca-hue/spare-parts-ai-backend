"""
app/config/logging.py — Structured logging setup.
"""

import logging
import sys


def configure_logging() -> None:
    from app.config.settings import settings
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    fmt   = (
        '{"time":"%(asctime)s","level":"%(levelname)s","module":"%(name)s","msg":"%(message)s"}'
        if settings.is_production
        else "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    logging.basicConfig(level=level, format=fmt,
                        handlers=[logging.StreamHandler(sys.stdout)], force=True)
    for noisy in ("httpx", "sqlalchemy.engine", "uvicorn.access"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
