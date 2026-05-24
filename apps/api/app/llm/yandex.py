from __future__ import annotations

from .base import BaseLLMClient, ChatMessage, CompletionResponse


class YandexGPTClient(BaseLLMClient):
    """Stub for the YandexGPT client. Real implementation lands Week 2 step 6
    (port + multi-tenant-ize the logic from legacy/app/llm/yandex.py).
    """

    provider = "yandex"

    def __init__(self, *, api_key: str, folder_id: str, model: str) -> None:
        self.api_key = api_key
        self.folder_id = folder_id
        self.model = model

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.1,
        max_tokens: int = 1500,
    ) -> CompletionResponse:
        raise NotImplementedError("YandexGPT client lands Week 2 — port from legacy/")

    async def embed(self, text: str) -> list[float]:
        raise NotImplementedError(
            "Embeddings go through OpenAI (text-embedding-3-small), not Yandex."
        )
