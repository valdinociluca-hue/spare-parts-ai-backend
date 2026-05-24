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


def _build_primary() -> BaseLLMClient:
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

    if provider == "anthropic":
        return _build_anthropic()

    raise ValueError(
        f"Unknown LLM_PROVIDER: '{provider}'. Use 'yandex', 'ollama' or 'anthropic'."
    )


def _build_anthropic() -> BaseLLMClient:
    from app.llm.anthropic_client import AnthropicClient
    logger.info("LLM fallback: Claude (%s)", settings.anthropic_model)
    return AnthropicClient(
        api_key     = settings.anthropic_api_key,
        model       = settings.anthropic_model,
        api_base    = settings.anthropic_api_base,
        temperature = settings.llm_temperature,
        max_tokens  = settings.llm_max_tokens,
        timeout     = settings.llm_timeout,
    )


def _build_client() -> BaseLLMClient:
    primary = _build_primary()

    # Wrap with Claude fallback when configured and not already the primary.
    if settings.anthropic_enabled and settings.llm_provider.lower() != "anthropic":
        from app.llm.fallback import FallbackLLMClient
        logger.info("Claude fallback enabled")
        return FallbackLLMClient(primary=primary, fallback=_build_anthropic())

    return primary


# Module-level singleton — instantiated once at import time
llm_client: BaseLLMClient = _build_client()
