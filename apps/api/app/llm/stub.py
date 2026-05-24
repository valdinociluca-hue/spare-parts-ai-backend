from __future__ import annotations

import hashlib

from .base import BaseLLMClient, ChatMessage, CompletionResponse


class StubLLMClient(BaseLLMClient):
    """Deterministic offline client. Used when no provider keys are set."""

    provider = "stub"

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.1,
        max_tokens: int = 1500,
    ) -> CompletionResponse:
        last_user = next((m.content for m in reversed(messages) if m.role == "user"), "")
        reply = f"[stub-llm] echo: {last_user[:200]}"
        return CompletionResponse(
            content=reply,
            tokens_used=len(reply.split()),
            provider="stub",
            model="stub-0",
        )

    async def embed(self, text: str) -> list[float]:
        # Deterministic pseudo-embedding so local tests can compare vectors.
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        return [b / 255.0 for b in digest * 48][:1536]
