"""
app/llm/ollama.py — Ollama client (local development / fallback).

Ollama exposes an OpenAI-compatible API at localhost:11434/v1.
No API keys, no geo-restrictions, free to run.

Recommended models (Russian language quality):
  qwen2.5:14b   — best Russian quality at reasonable hardware cost
  qwen2.5:7b    — lighter, still decent Russian
  mistral:7b    — acceptable Russian

Install Ollama: https://ollama.com
Pull a model:   ollama pull qwen2.5:14b
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


class OllamaClient(BaseLLMClient):
    """
    OpenAI-compatible client for Ollama local server.
    Converts our internal message format (uses "text") to OpenAI format (uses "content").
    """

    def __init__(self, api_base: str, model: str,
                 temperature: float, max_tokens: int, timeout: float):
        self.api_base    = api_base.rstrip("/")
        self.model       = model
        self.temperature = temperature
        self.max_tokens  = max_tokens
        self.timeout     = timeout

    def _to_openai_messages(self, messages: list[dict]) -> list[dict]:
        """Convert internal format (text) → OpenAI format (content)."""
        return [{"role": m["role"], "content": m["text"]} for m in messages]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _post(self, payload: dict) -> dict:
        url = f"{self.api_base}/chat/completions"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url, json=payload,
                headers={"Content-Type": "application/json"},
            )

        if not response.is_success:
            raise LLMAPIError(f"Ollama error {response.status_code}: {response.text[:300]}")

        return response.json()

    async def chat(self, messages: list[dict], temperature: float | None = None) -> str:
        temp    = temperature if temperature is not None else self.temperature
        payload = {
            "model":       self.model,
            "messages":    self._to_openai_messages(messages),
            "temperature": temp,
            "max_tokens":  self.max_tokens,
            "stream":      False,
            # Request JSON output — supported by most Ollama models
            "response_format": {"type": "json_object"},
        }

        t0 = time.monotonic()
        data = await self._post(payload)
        latency_ms = (time.monotonic() - t0) * 1000

        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise LLMParseError(f"Unexpected Ollama response structure: {e}")

        logger.debug("Ollama %s (%.0fms): %s", self.model, latency_ms, text[:200])
        return text
