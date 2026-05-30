"""Claude (Anthropic) client for GLOBAL tenants.

Uses the official ``anthropic`` SDK. Stubs out if no API key is configured.
"""

from __future__ import annotations

import logging

from anthropic import APIError as AnthropicAPIError
from anthropic import AsyncAnthropic
from fastapi import HTTPException, status

from .base import BaseLLMClient, ChatMessage, CompletionResponse
from .stub import StubLLMClient

logger = logging.getLogger(__name__)


class ClaudeClient(BaseLLMClient):
    """Anthropic Claude client. Falls back to a stub when no API key is set."""

    provider = "claude"

    def __init__(self, *, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model
        self._stub = StubLLMClient() if not api_key else None
        self._client = AsyncAnthropic(api_key=api_key) if api_key else None

    @staticmethod
    def _split_messages(
        messages: list[ChatMessage],
    ) -> tuple[str | None, list[dict[str, str]]]:
        """Anthropic requires alternating user/assistant turns and a separate
        top-level ``system`` string. Collapse consecutive same-role turns and
        ensure the conversation starts with a user message."""
        system_parts: list[str] = []
        convo: list[dict[str, str]] = []
        for msg in messages:
            if msg.role == "system":
                if msg.content:
                    system_parts.append(msg.content)
                continue
            role = "assistant" if msg.role == "assistant" else "user"
            if convo and convo[-1]["role"] == role:
                convo[-1]["content"] += "\n\n" + msg.content
            else:
                convo.append({"role": role, "content": msg.content})

        if convo and convo[0]["role"] != "user":
            convo.insert(0, {"role": "user", "content": "(start)"})
        if not convo:
            convo = [{"role": "user", "content": "(empty)"}]

        system_text = "\n\n".join(system_parts) if system_parts else None
        return system_text, convo

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.1,
        max_tokens: int = 1500,
    ) -> CompletionResponse:
        if self._client is None:
            assert self._stub is not None
            return await self._stub.chat(
                messages, temperature=temperature, max_tokens=max_tokens
            )

        system_text, convo = self._split_messages(messages)
        kwargs: dict[str, object] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": convo,
        }
        if system_text:
            kwargs["system"] = system_text

        try:
            response = await self._client.messages.create(**kwargs)
        except AnthropicAPIError as exc:
            logger.error("Anthropic API error: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Anthropic error: {exc}",
            ) from exc

        text = "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        )
        tokens_used = (response.usage.input_tokens or 0) + (
            response.usage.output_tokens or 0
        )

        return CompletionResponse(
            content=text,
            tokens_used=tokens_used,
            provider="claude",
            model=self.model,
        )

    async def embed(self, text: str) -> list[float]:
        raise NotImplementedError(
            "Embeddings go through OpenAI (text-embedding-3-small), not Claude."
        )
