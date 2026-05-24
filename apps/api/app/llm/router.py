from __future__ import annotations

from typing import TYPE_CHECKING

from app.config import settings

from .base import BaseLLMClient
from .claude import ClaudeClient
from .stub import StubLLMClient
from .yandex import YandexGPTClient

if TYPE_CHECKING:
    from app.tenancy import Tenant


def get_llm_for_tenant(tenant: Tenant) -> BaseLLMClient:
    """Return the LLM client for this tenant based on tenant.llm_provider.

    Falls back to StubLLMClient when no provider key is configured — keeps
    local dev unblocked while real keys are being provisioned.
    """
    if settings.use_stub_llm:
        return StubLLMClient()

    if tenant.llm_provider == "yandex":
        return YandexGPTClient(
            api_key=settings.yandex_api_key,
            folder_id=settings.yandex_folder_id,
            model=settings.yandex_gpt_model,
        )
    if tenant.llm_provider == "claude":
        return ClaudeClient(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
        )
    raise ValueError(f"Unknown llm_provider for tenant {tenant.slug}: {tenant.llm_provider}")
