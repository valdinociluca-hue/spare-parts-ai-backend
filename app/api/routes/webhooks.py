"""
app/api/routes/webhooks.py — Inbound webhook endpoints.

Always returns HTTP 200 to Bitrix — non-2xx triggers Bitrix retries
which cause duplicate records. Errors are in the response body.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.db.session import get_session
from app.integrations.bitrix import parse_webhook
from app.services.request_service import RequestService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/bitrix")
async def bitrix_webhook(
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    # Optional secret validation
    if settings.bitrix_webhook_secret:
        provided = (
            request.query_params.get("secret")
            or request.headers.get("X-Webhook-Secret")
        )
        if provided != settings.bitrix_webhook_secret:
            raise HTTPException(status_code=401, detail="Invalid webhook secret")

    # Parse body (JSON or form-encoded)
    content_type = request.headers.get("content-type", "")
    try:
        raw: dict[str, Any] = (
            await request.json()
            if "application/json" in content_type
            else dict(await request.form())
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cannot parse body: {e}")

    if not raw:
        raise HTTPException(status_code=400, detail="Empty body")

    incoming = parse_webhook(raw)
    result   = await RequestService(db).handle_incoming(incoming)

    return {
        "status":     result.status.value,
        "request_id": result.request_id,
        "escalate":   result.escalate_to_human,
        "error":      result.error,
    }


# ── Dev test endpoint ─────────────────────────────────────────────────────────

@router.post("/test", include_in_schema=not settings.is_production)
async def test_message(
    body: dict[str, Any],
    db: AsyncSession = Depends(get_session),
):
    """Dev only: POST {"message": "..."} to test classification without Bitrix."""
    if settings.is_production:
        raise HTTPException(status_code=404)

    msg = body.get("message", "").strip()
    if not msg:
        raise HTTPException(status_code=400, detail="'message' required")

    incoming = parse_webhook({
        "data": {"FIELDS": {"ID": "DEV-TEST", "COMMENTS": msg}}
    })
    result = await RequestService(db).handle_incoming(incoming)
    return result.model_dump()
