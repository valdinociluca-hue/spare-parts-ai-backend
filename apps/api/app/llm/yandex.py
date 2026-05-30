"""YandexGPT client for tenants in the RU region.

API reference: https://yandex.cloud/docs/foundation-models/text-generation/api-ref/

Yandex quirks the client has to absorb:
  - Auth uses ``Authorization: Api-Key <key>`` + ``x-folder-id`` header.
  - Model URI is ``gpt://<folder>/<model>/latest``.
  - Messages take a ``text`` field (not ``content``).
  - ``maxTokens`` is sent as a string.
  - The response payload is ``result.alternatives[0].message.text`` and the
    usage counters live under ``result.usage``.
"""

from __future__ import annotations

import logging

import httpx
from fastapi import HTTPException, status

from .base import BaseLLMClient, ChatMessage, CompletionResponse
from .stub import StubLLMClient

logger = logging.getLogger(__name__)

COMPLETION_PATH = "/foundationModels/v1/completion"


class YandexGPTClient(BaseLLMClient):
    """YandexGPT Pro client. Falls back to a stub when the API key is empty."""

    provider = "yandex"

    def __init__(
        self,
        *,
        api_key: str,
        folder_id: str,
        model: str,
        api_base: str = "https://llm.api.cloud.yandex.net",
        timeout: float = 45.0,
    ) -> None:
        self.api_key = api_key
        self.folder_id = folder_id
        self.model = model
        self.api_base = api_base.rstrip("/")
        self.timeout = timeout
        self._stub = StubLLMClient() if not (api_key and folder_id) else None

    @property
    def model_uri(self) -> str:
        return f"gpt://{self.folder_id}/{self.model}/latest"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Api-Key {self.api_key}",
            "x-folder-id": self.folder_id,
            "Content-Type": "application/json",
        }

    @staticmethod
    def _to_yandex_messages(messages: list[ChatMessage]) -> list[dict[str, str]]:
        return [{"role": m.role, "text": m.content} for m in messages]

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.1,
        max_tokens: int = 1500,
    ) -> CompletionResponse:
        if self._stub is not None:
            return await self._stub.chat(
                messages, temperature=temperature, max_tokens=max_tokens
            )

        payload = {
            "modelUri": self.model_uri,
            "completionOptions": {
                "stream": False,
                "temperature": temperature,
                "maxTokens": str(max_tokens),
            },
            "messages": self._to_yandex_messages(messages),
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                self.api_base + COMPLETION_PATH,
                json=payload,
                headers=self._headers(),
            )

        if response.status_code in (401, 403):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="YandexGPT auth failed — check YANDEX_API_KEY / folder",
            )
        if response.status_code == 429:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="YandexGPT rate limit exceeded",
            )
        if not response.is_success:
            logger.error("YandexGPT %s: %s", response.status_code, response.text[:500])
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"YandexGPT error {response.status_code}",
            )

        data = response.json()
        try:
            text = data["result"]["alternatives"][0]["message"]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            logger.error("YandexGPT unexpected payload: %s", data)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="YandexGPT returned an unexpected response shape",
            ) from exc

        usage = data.get("result", {}).get("usage", {}) or {}
        tokens_used = int(usage.get("totalTokens") or 0)

        return CompletionResponse(
            content=text,
            tokens_used=tokens_used,
            provider="yandex",
            model=self.model,
        )

    async def embed(self, text: str) -> list[float]:
        raise NotImplementedError(
            "Embeddings go through OpenAI (text-embedding-3-small), not Yandex."
        )
