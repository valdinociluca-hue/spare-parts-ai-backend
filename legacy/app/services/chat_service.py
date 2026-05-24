"""
app/services/chat_service.py — Orchestrates one chat turn end-to-end.

Flow per turn:
  1. Load or create conversation + context
  2. Persist user message
  3. Run ConversationAgent (ReAct loop)
  4. Persist assistant message + tool call records
  5. Save updated context
  6. If escalated: mark conversation + create Escalation record
  7. Commit + return ChatResponse
"""

import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.conversation_agent import ConversationAgent
from app.chat.state import ConversationManager
from app.core.schemas import ChatRequest, ChatResponse
from app.db.models import Escalation

logger = logging.getLogger(__name__)


class ChatService:

    def __init__(self, db: AsyncSession):
        self._db      = db
        self._manager = ConversationManager(db)

    async def handle(self, request: ChatRequest) -> ChatResponse:
        conversation_id, context = await self._manager.get_or_create(request.session_id)

        # Persist user message
        await self._manager.append_message(
            conversation_id, role="user", content=request.message
        )

        context.turn_count += 1

        # Load recent history for the LLM
        history = await self._manager.load_recent_messages(conversation_id)
        # The user message was just appended — load_recent_messages includes it,
        # so strip the last item (it becomes user_message below)
        if history and history[-1]["role"] == "user":
            history = history[:-1]

        # Run agent
        agent  = ConversationAgent(session=self._db, context=context)
        result = await agent.run({"history": history, "user_message": request.message})

        # Persist assistant response
        await self._manager.append_message(
            conversation_id, role="assistant", content=result.response
        )

        # Persist tool call records as tool messages
        for tc in result.tool_calls:
            await self._manager.append_message(
                conversation_id,
                role="tool",
                content=str(tc.result),
                tool_name=tc.tool,
                tool_result=tc.result,
            )

        # Update and save context
        context.tools_called.extend(tc.tool for tc in result.tool_calls)
        await self._manager.save_context(conversation_id, context)

        # Handle escalation
        if result.escalated and not context.escalation_reason == "__already_saved":
            await self._manager.mark_escalated(conversation_id)
            existing = await self._db.get(Escalation, conversation_id)
            if not existing:
                self._db.add(Escalation(
                    conversation_id=conversation_id,
                    reason=context.escalation_reason or "Автоматическая эскалация",
                    state_snapshot=context.model_dump(),
                    status="pending",
                ))
            context.escalation_reason = "__already_saved"
            await self._manager.save_context(conversation_id, context)

        await self._db.commit()

        return ChatResponse(
            session_id=conversation_id,
            response=result.response,
            tool_calls=result.tool_calls,
            escalated=result.escalated,
            confidence=result.confidence,
        )
