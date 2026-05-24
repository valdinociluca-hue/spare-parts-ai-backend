"""
app/chat/state.py — Conversation session management.

ConversationManager: load, save, and update ConversationContext from the DB.
Sessions are identified by conversation UUID stored in a browser cookie.
"""

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.schemas import ConversationContext
from app.db.models import Conversation, ConversationState, Message

logger = logging.getLogger(__name__)

# How many recent messages to load into the LLM context window
CONTEXT_WINDOW_MESSAGES = 20


class ConversationManager:

    def __init__(self, session: AsyncSession):
        self._db = session

    async def get_or_create(self, session_id: str | None) -> tuple[str, ConversationContext]:
        """
        Load an existing conversation or create a new one.
        Returns (conversation_id, context).
        """
        if session_id:
            conv = await self._db.get(Conversation, session_id)
            if conv and conv.status != "escalated":
                ctx = await self._load_context(session_id)
                return session_id, ctx

        # Create new conversation
        conv = Conversation(channel="web", status="active")
        self._db.add(conv)
        await self._db.flush()   # get the generated ID

        state_row = ConversationState(
            conversation_id=conv.id,
            state=ConversationContext().model_dump(),
        )
        self._db.add(state_row)
        await self._db.flush()

        return conv.id, ConversationContext()

    async def _load_context(self, conversation_id: str) -> ConversationContext:
        state_row = await self._db.get(ConversationState, conversation_id)
        if state_row and state_row.state:
            try:
                return ConversationContext.model_validate(state_row.state)
            except Exception:
                pass
        return ConversationContext()

    async def save_context(self, conversation_id: str, context: ConversationContext) -> None:
        state_row = await self._db.get(ConversationState, conversation_id)
        if state_row:
            state_row.state      = context.model_dump()
            state_row.updated_at = datetime.utcnow()
        else:
            self._db.add(ConversationState(
                conversation_id=conversation_id,
                state=context.model_dump(),
            ))

    async def append_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        tool_name: str | None = None,
        tool_result=None,
    ) -> None:
        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            tool_name=tool_name,
            tool_result=tool_result,
        )
        self._db.add(msg)

    async def load_recent_messages(self, conversation_id: str) -> list[dict]:
        """
        Load the last CONTEXT_WINDOW_MESSAGES messages as dicts
        suitable for LLM prompt injection.
        """
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(CONTEXT_WINDOW_MESSAGES)
        )
        rows = (await self._db.execute(stmt)).scalars().all()
        rows = list(reversed(rows))   # chronological order

        result = []
        for m in rows:
            if m.role == "tool":
                result.append({
                    "role":    "assistant",
                    "text":    f"[Tool: {m.tool_name}] Result: {m.content}",
                })
            else:
                result.append({"role": m.role, "text": m.content})
        return result

    async def mark_escalated(self, conversation_id: str) -> None:
        conv = await self._db.get(Conversation, conversation_id)
        if conv:
            conv.status     = "escalated"
            conv.updated_at = datetime.utcnow()

    async def mark_resolved(self, conversation_id: str) -> None:
        conv = await self._db.get(Conversation, conversation_id)
        if conv:
            conv.status     = "resolved"
            conv.updated_at = datetime.utcnow()
