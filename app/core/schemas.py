"""
app/core/schemas.py — Shared domain types used across all layers.

IncomingRequest is the normalised, channel-agnostic representation of
any customer message. All integrations (Bitrix, Telegram, email) produce
one of these — the pipeline never sees raw webhook payloads.
"""

from enum import Enum
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class RequestCategory(str, Enum):
    SPARE_PART_SELECTION  = "spare_part_selection"
    INVOICE_REQUEST       = "invoice_request"
    DOCUMENTATION_REQUEST = "documentation_request"
    OTHER                 = "other"


class RequestStatus(str, Enum):
    PENDING      = "pending"
    CLASSIFIED   = "classified"
    DRAFT_READY  = "draft_ready"
    SENT_TO_TEAM = "sent_to_team"
    ERROR        = "error"


class IncomingRequest(BaseModel):
    """Normalised customer request — independent of the source channel."""
    source_channel:  str            # "bitrix" | "telegram" | "email" | "max"
    external_id:     str            # ID in the originating system
    message_text:    str
    contact_name:    Optional[str]  = None
    contact_email:   Optional[str]  = None
    contact_phone:   Optional[str]  = None
    received_at:     datetime       = Field(default_factory=datetime.utcnow)


class PipelineResult(BaseModel):
    """Combined output of the agent orchestration pipeline."""
    request_id:        str
    category:          Optional[RequestCategory] = None
    confidence:        Optional[float]           = None
    escalate_to_human: bool                      = True
    draft_reply:       str                       = ""
    missing_fields:    list[str]                 = []
    status:            RequestStatus             = RequestStatus.PENDING
    error:             Optional[str]             = None
