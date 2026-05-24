from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Literal

from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class CompletionResponse(BaseModel):
    content: str
    tokens_used: int
    provider: Literal["yandex", "claude", "stub"]
    model: str


class BaseLLMClient(ABC):
    provider: Literal["yandex", "claude", "stub"]

    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.1,
        max_tokens: int = 1500,
    ) -> CompletionResponse: ...

    @abstractmethod
    async def embed(self, text: str) -> list[float]: ...
