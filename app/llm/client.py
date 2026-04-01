"""
app/llm/client.py — LLM client factory.

Returns the correct BaseLLMClient implementation based on LLM_PROVIDER env var.
Agents import `llm_client` from this module — they never instantiate providers directly.

Switching provider = change LLM_PROVIDER in .env. No code changes needed.
"""

import logging

from app.config.settings import settings
from app.llm.base import BaseLLMClient

logger = logging.getLogger(__name__)


def _build_client() -> BaseLLMClient:
    provider = settings.llm_provider.lower()

    if provider == "yandex":
        from app.llm.yandex import YandexGPTClient
        logger.info("LLM provider: YandexGPT (%s)", settings.yandex_gpt_model)
        return YandexGPTClient(
            api_key     = settings.yandex_api_key,
            folder_id   = settings.yandex_folder_id,
            model       = settings.yandex_gpt_model,
            api_base    = settings.yandex_api_base,
            temperature = settings.llm_temperature,
            max_tokens  = settings.llm_max_tokens,
            timeout     = settings.llm_timeout,
        )

    if provider == "ollama":
        from app.llm.ollama import OllamaClient
        logger.info("LLM provider: Ollama (%s)", settings.ollama_model)
        return OllamaClient(
            api_base    = settings.ollama_api_base,
            model       = settings.ollama_model,
            temperature = settings.llm_temperature,
            max_tokens  = settings.llm_max_tokens,
            timeout     = settings.llm_timeout,
        )

    raise ValueError(f"Unknown LLM_PROVIDER: '{provider}'. Use 'yandex' or 'ollama'.")


# Module-level singleton — instantiated once at import time
llm_client: BaseLLMClient = _build_client()
