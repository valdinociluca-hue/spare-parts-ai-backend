"""
app/llm/anthropic_client.py — Claude (Anthropic Messages API) client.

Used as the fallback provider when YandexGPT is unavailable or for
complex queries. Implements the same BaseLLMClient interface, so the
ConversationAgent never knows which provider answered.

API reference: https://docs.claude.com/en/api/messages

Mapping from our internal message format ({"role", "text"}):
  - role "system"          → top-level `system` string (concatenated)
  - role "user"/"assistant"→ messages[] with `content`
  - consecutive same-role messages are merged (Anthropic requires
    strictly alternating user/assistant turns starting with user)
"""

import logging
import time

import httpx
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.exceptions import LLMAPIError, LLMParseError
from app.llm.base import BaseLLMClient

logger = logging.getLogger(__name__)

MESSAGES_URL = "/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


class AnthropicClient(BaseLLMClient):
    """Client for Claude via the Anthropic Messages API."""

    def __init__(self, api_key: str, model: str, api_base: str,
                 temperature: float, max_tokens: int, timeout: float):
        self.api_key     = api_key
        self.model       = model
        self.api_base    = api_base.rstrip("/")
        self.temperature = temperature
        self.max_tokens  = max_tokens
        self.timeout     = timeout

    def _headers(self) -> dict:
        return {
            "x-api-key":         self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type":      "application/json",
        }

    @staticmethod
    def _split_messages(messages: list[dict]) -> tuple[str, list[dict]]:
        """Extract system text and build an alternating user/assistant list."""
        system_parts: list[str] = []
        convo: list[dict] = []

        for m in messages:
            role = m.get("role", "user")
            text = m.get("text") or m.get("content") or ""
            if role == "system":
                if text:
                    system_parts.append(text)
                continue
            role = "assistant" if role == "assistant" else "user"
            if convo and convo[-1]["role"] == role:
                convo[-1]["content"] += "\n\n" + text
            else:
                convo.append({"role": role, "content": text})

        # Anthropic requires the first message to be from the user.
        if convo and convo[0]["role"] != "user":
            convo.insert(0, {"role": "user", "content": "(начало диалога)"})
        if not convo:
            convo = [{"role": "user", "content": "(пустой запрос)"}]

        return "\n\n".join(system_parts), convo

    def _build_payload(self, messages: list[dict], temperature: float) -> dict:
        system, convo = self._split_messages(messages)
        payload = {
            "model":       self.model,
            "max_tokens":  self.max_tokens,
            "temperature": temperature,
            "messages":    convo,
        }
        if system:
            payload["system"] = system
        return payload

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _post(self, payload: dict) -> dict:
        url = self.api_base + MESSAGES_URL
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload, headers=self._headers())

        if response.status_code == 401:
            raise LLMAPIError("Anthropic auth failed — check ANTHROPIC_API_KEY")
        if response.status_code == 403:
            raise LLMAPIError("Anthropic forbidden — key lacks access to this model")
        if response.status_code == 429:
            raise LLMAPIError("Anthropic rate limit exceeded")
        if response.status_code >= 500:
            response.raise_for_status()   # triggers tenacity retry
        if not response.is_success:
            raise LLMAPIError(
                f"Anthropic error {response.status_code}: {response.text[:300]}"
            )

        return response.json()

    async def chat(self, messages: list[dict], temperature: float | None = None) -> str:
        temp    = temperature if temperature is not None else self.temperature
        payload = self._build_payload(messages, temp)

        t0 = time.monotonic()
        data = await self._post(payload)
        latency_ms = (time.monotonic() - t0) * 1000

        try:
            # content is a list of blocks; concatenate all text blocks
            blocks = data["content"]
            text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        except (KeyError, IndexError, TypeError) as e:
            raise LLMParseError(f"Unexpected Anthropic response structure: {e} | {data}")

        logger.debug("Claude (%.0fms): %s", latency_ms, text[:200])
        return text
