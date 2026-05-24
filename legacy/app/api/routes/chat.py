"""
app/api/routes/chat.py — Website chat endpoints.

POST /api/v1/chat
  Body:   {message: str, session_id?: str}
  Cookie: session_id (read + write for persistence)
  Returns: ChatResponse + sets session_id cookie

GET /api/v1/chat/{session_id}/history
  Returns the last N messages for a session (for UI reload on page return)
"""

import logging

from fastapi import APIRouter, Cookie, Depends, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.core.schemas import ChatRequest, ChatResponse
from app.db.models import Conversation, Message
from app.db.session import get_session
from app.services.chat_service import ChatService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

_COOKIE_NAME = "sparechat_session"


@router.post("", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    response: Response,
    session_cookie: str | None = Cookie(default=None, alias=_COOKIE_NAME),
    db: AsyncSession = Depends(get_session),
):
    """
    Send a message to the AI spare parts consultant.

    Session resolution order:
      1. session_id in request body (explicit override)
      2. sparechat_session cookie (returning visitor)
      3. None → new conversation created
    """
    session_id = body.session_id or session_cookie

    result = await ChatService(db).handle(
        ChatRequest(message=body.message, session_id=session_id)
    )

    # Set / refresh session cookie
    response.set_cookie(
        key=_COOKIE_NAME,
        value=result.session_id,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
    )

    return result


@router.get("/{session_id}/history")
async def get_history(
    session_id: str,
    db: AsyncSession = Depends(get_session),
    limit: int = 30,
):
    """Return recent messages for a session (for page-reload continuity)."""
    conv = await db.get(Conversation, session_id)
    if not conv:
        return {"session_id": session_id, "messages": []}

    stmt = (
        select(Message)
        .where(Message.conversation_id == session_id)
        .where(Message.role.in_(["user", "assistant"]))   # exclude tool internals
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()
    rows = list(reversed(rows))

    return {
        "session_id": session_id,
        "status":     conv.status,
        "messages": [
            {
                "role":       m.role,
                "content":    m.content,
                "created_at": m.created_at.isoformat(),
            }
            for m in rows
        ],
    }
