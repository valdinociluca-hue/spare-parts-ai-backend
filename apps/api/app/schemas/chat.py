from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


Role = Literal["user", "assistant", "system"]
Module = Literal["parts_id", "technician", "order"]


class ChatMessageIn(BaseModel):
    session_token: str
    module: Module = "parts_id"
    content: str


class ChatMessageOut(BaseModel):
    id: UUID
    role: Role
    content: str
    created_at: datetime


class ChatResponse(BaseModel):
    reply: ChatMessageOut
    skus_mentioned: list[str] = []
