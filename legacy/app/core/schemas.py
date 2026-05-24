"""
app/core/schemas.py — Shared domain types across all layers.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# Equipment identification (built up during conversation)
# ─────────────────────────────────────────────────────────────────────────────

class EquipmentContext(BaseModel):
    brand:      Optional[str] = None
    model_name: Optional[str] = None
    model_code: Optional[str] = None
    serial:     Optional[str] = None

    @property
    def is_complete(self) -> bool:
        return bool(self.brand and self.model_code)


# ─────────────────────────────────────────────────────────────────────────────
# Conversation state (persisted as JSONB per conversation)
# ─────────────────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role:        str                       # user | assistant | tool
    content:     str
    tool_name:   Optional[str] = None      # set when role=tool
    tool_result: Optional[Any] = None
    created_at:  datetime = Field(default_factory=datetime.utcnow)


class ConversationContext(BaseModel):
    """
    Structured state tracked across turns.
    Persisted as JSON in conversation_state.state.
    """
    equipment:         EquipmentContext = Field(default_factory=EquipmentContext)

    reported_symptoms: list[str] = Field(default_factory=list)
    confirmed_facts:   list[str] = Field(default_factory=list)
    ruled_out:         list[str] = Field(default_factory=list)

    turn_count:        int = 0
    questions_asked:   list[str] = Field(default_factory=list)
    tools_called:      list[str] = Field(default_factory=list)

    last_confidence:   Optional[float] = None
    candidate_skus:    list[str] = Field(default_factory=list)

    escalated:         bool = False
    escalation_reason: Optional[str] = None

    def should_escalate(self, confidence_threshold: float = 0.5) -> bool:
        if self.escalated:
            return True
        if self.turn_count > 15:
            return True
        if self.last_confidence is not None and self.last_confidence < confidence_threshold:
            return True
        return False


# ─────────────────────────────────────────────────────────────────────────────
# ReAct tool-dispatch output (parsed from LLM JSON)
# ─────────────────────────────────────────────────────────────────────────────

class ReActOutput(BaseModel):
    thought: str
    action:  str                    # tool name OR "respond"
    args:    dict[str, Any] = Field(default_factory=dict)
    text:    Optional[str] = None   # set when action="respond"


# ─────────────────────────────────────────────────────────────────────────────
# Chat API request / response
# ─────────────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message:    str
    session_id: Optional[str] = None   # None = start new conversation


class ToolCallRecord(BaseModel):
    tool:   str
    args:   dict[str, Any]
    result: Any


class ChatResponse(BaseModel):
    session_id: str
    response:   str
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    escalated:  bool = False
    confidence: Optional[float] = None


# ─────────────────────────────────────────────────────────────────────────────
# Retrieval results (returned by search tools)
# ─────────────────────────────────────────────────────────────────────────────

class PartResult(BaseModel):
    sku:               str
    name:              str
    description:       Optional[str] = None
    brand:             Optional[str] = None
    category:          Optional[str] = None
    price:             Optional[float] = None
    stock_qty:         Optional[int] = None
    compatible_models: list[str] = Field(default_factory=list)
    source_url:        Optional[str] = None
    score:             float = 0.0


class DocumentResult(BaseModel):
    chunk_id:     str
    source_url:   Optional[str] = None
    title:        Optional[str] = None
    content:      str
    section_type: Optional[str] = None
    page_num:     Optional[int] = None
    score:        float = 0.0
