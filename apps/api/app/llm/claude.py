from __future__ import annotations

from .base import BaseLLMClient, ChatMessage, CompletionResponse


class ClaudeClient(BaseLLMClient):
    """Stub for the Claude client. Real implementation lands Week 2 step 6
    (will use the anthropic SDK; key in settings.anthropic_api_key).
    """

    provider = "claude"

    def __init__(self, *, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.1,
        max_tokens: int = 1500,
    ) -> CompletionResponse:
        raise NotImplementedError("Claude client lands Week 2 — wire anthropic SDK here.")

    async def embed(self, text: str) -> list[float]:
        raise NotImplementedError(
            "Embeddings go through OpenAI (text-embedding-3-small), not Claude."
        )
