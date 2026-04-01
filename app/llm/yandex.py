"""
app/llm/yandex.py — YandexGPT Pro client.

API reference: https://yandex.cloud/ru/docs/foundation-models/text-generation/api-ref/

Key differences from OpenAI API:
  - Auth: "Authorization: Api-Key {key}" + "x-folder-id: {folder_id}"
  - Model URI: "gpt://{folder_id}/yandexgpt/latest"
  - Request body uses "messages[].text" not "messages[].content"
  - maxTokens is a STRING not an integer
  - Response is nested: result.alternatives[0].message.text
  - No native JSON mode — we enforce JSON via prompt instructions
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

COMPLETION_URL = "/foundationModels/v1/completion"


class YandexGPTClient(BaseLLMClient):
    """
    Client for YandexGPT Pro via Yandex Cloud Foundation Models API.
    Accessible from Russia without VPN. Billed in rubles.
    """

    def __init__(self, api_key: str, folder_id: str, model: str,
                 api_base: str, temperature: float, max_tokens: int, timeout: float):
        self.api_key     = api_key
        self.folder_id   = folder_id
        self.model_uri   = f"gpt://{folder_id}/{model}/latest"
        self.api_base    = api_base.rstrip("/")
        self.temperature = temperature
        self.max_tokens  = max_tokens
        self.timeout     = timeout

    def _headers(self) -> dict:
        return {
            "Authorization": f"Api-Key {self.api_key}",
            "x-folder-id":   self.folder_id,
            "Content-Type":  "application/json",
        }

    def _build_payload(self, messages: list[dict], temperature: float) -> dict:
        # YandexGPT uses "text" field; callers use "text" already (our internal format)
        return {
            "modelUri": self.model_uri,
            "completionOptions": {
                "stream":      False,
                "temperature": temperature,
                "maxTokens":   str(self.max_tokens),   # must be string
            },
            "messages": messages,
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _post(self, payload: dict) -> dict:
        url = self.api_base + COMPLETION_URL
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload, headers=self._headers())

        if response.status_code == 401:
            raise LLMAPIError("YandexGPT auth failed — check YANDEX_API_KEY")
        if response.status_code == 403:
            raise LLMAPIError("YandexGPT forbidden — check YANDEX_FOLDER_ID and IAM role")
        if response.status_code == 429:
            raise LLMAPIError("YandexGPT rate limit exceeded")
        if response.status_code >= 500:
            response.raise_for_status()   # triggers tenacity retry
        if not response.is_success:
            raise LLMAPIError(f"YandexGPT error {response.status_code}: {response.text[:300]}")

        return response.json()

    async def chat(self, messages: list[dict], temperature: float | None = None) -> str:
        temp    = temperature if temperature is not None else self.temperature
        payload = self._build_payload(messages, temp)

        t0 = time.monotonic()
        data = await self._post(payload)
        latency_ms = (time.monotonic() - t0) * 1000

        try:
            text = data["result"]["alternatives"][0]["message"]["text"]
        except (KeyError, IndexError) as e:
            raise LLMParseError(f"Unexpected YandexGPT response structure: {e} | {data}")

        logger.debug("YandexGPT (%.0fms): %s", latency_ms, text[:200])
        return text
