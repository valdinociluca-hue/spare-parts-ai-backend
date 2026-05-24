from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter

from app.deps import CurrentTenant, Tenant
from app.llm.router import get_llm_for_tenant
from app.llm.base import ChatMessage as LLMMessage
from app.schemas import ChatMessageIn, ChatMessageOut, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/messages", response_model=ChatResponse)
async def post_message(
    payload: ChatMessageIn,
    tenant: Tenant = CurrentTenant,
) -> ChatResponse:
    """Module 2/3 entry point. Phase 1 scaffold routes through the LLM (or
    stub) so we can see the full path light up locally before any RAG is
    wired in Week 2."""
    llm = get_llm_for_tenant(tenant)
    completion = await llm.chat(
        messages=[LLMMessage(role="user", content=payload.content)],
    )
    reply = ChatMessageOut(
        id=uuid4(),
        role="assistant",
        content=completion.content,
        created_at=datetime.now(timezone.utc),
    )
    return ChatResponse(reply=reply, skus_mentioned=[])
