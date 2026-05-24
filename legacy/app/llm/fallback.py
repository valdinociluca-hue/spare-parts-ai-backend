"""
app/llm/fallback.py — Primary → fallback LLM wrapper.

Tries the primary provider (YandexGPT in production). On any LLM error
(network, auth, rate-limit, 5xx, parse failure) it transparently retries
the same request against the fallback provider (Claude).

Agents depend only on BaseLLMClient — they never know a fallback occurred.
"""

import logging

from app.core.exceptions import LLMError
from app.llm.base import BaseLLMClient

logger = logging.getLogger(__name__)


class FallbackLLMClient(BaseLLMClient):

    def __init__(self, primary: BaseLLMClient, fallback: BaseLLMClient):
        self._primary  = primary
        self._fallback = fallback

    async def chat(self, messages: list[dict], temperature: float | None = None) -> str:
        try:
            return await self._primary.chat(messages, temperature=temperature)
        except LLMError as e:
            logger.warning(
                "Primary LLM failed (%s) — falling back to %s",
                e, type(self._fallback).__name__,
            )
            return await self._fallback.chat(messages, temperature=temperature)
