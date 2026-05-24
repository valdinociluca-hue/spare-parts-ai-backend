"""
app/config/settings.py — Centralised, type-safe configuration.

All runtime config is read from environment variables (or .env file).
Validated at startup — process fails immediately on missing required vars.

Import `settings` from this module. Never read os.environ directly.
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────
    app_name:    str = "spare-parts-ai-backend"
    app_version: str = "0.1.0"
    environment: str = "development"
    log_level:   str = "INFO"

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    # ── Database ──────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/spare_parts"

    # ── LLM provider selection ────────────────────────────────
    # "yandex" in production, "ollama" in local development
    llm_provider: str = "yandex"

    # ── YandexGPT (production) ────────────────────────────────
    # API key from Yandex Cloud console → Service accounts → API keys
    yandex_api_key:    str = "REPLACE_ME"
    # Folder ID from Yandex Cloud console (top-left dropdown)
    yandex_folder_id:  str = "REPLACE_ME"
    # "yandexgpt" = Pro, "yandexgpt-lite" = fast/cheap
    yandex_gpt_model:  str = "yandexgpt"
    yandex_api_base:   str = "https://llm.api.cloud.yandex.net"

    # ── Ollama (local development / fallback) ─────────────────
    ollama_api_base:   str = "http://localhost:11434/v1"
    ollama_model:      str = "qwen2.5:14b"

    # ── Claude / Anthropic (fallback for complex queries) ─────
    # Leave anthropic_api_key empty to disable the fallback entirely.
    anthropic_api_key:  str = ""
    anthropic_model:    str = "claude-sonnet-4-6"
    anthropic_api_base: str = "https://api.anthropic.com"

    @property
    def anthropic_enabled(self) -> bool:
        return bool(self.anthropic_api_key and "REPLACE" not in self.anthropic_api_key)

    # ── Shared LLM settings ───────────────────────────────────
    llm_temperature:   float = 0.1
    llm_max_tokens:    int   = 1500
    llm_timeout:       float = 45.0

    # ── VK Teams ──────────────────────────────────────────────
    vk_teams_bot_token: str = "REPLACE_ME"
    vk_teams_chat_id:   str = "REPLACE_ME"
    vk_teams_api_base:  str = "https://api.internal.myteam.mail.ru/bot/v1"

    # ── Bitrix ────────────────────────────────────────────────
    bitrix_webhook_secret: Optional[str] = None

    # ── Processing ────────────────────────────────────────────
    confidence_threshold: float = 0.6
    draft_only_mode:      bool  = True

    # ── Embeddings ────────────────────────────────────────────
    # paraphrase-multilingual-mpnet-base-v2 = 768d, good Russian support
    embedding_model: str = "paraphrase-multilingual-mpnet-base-v2"
    vector_dim:      int = 768

    # ── Website chat ──────────────────────────────────────────
    # Allowed CORS origins for the website widget
    website_origins: str = "https://lvtrade.ru,https://www.lvtrade.ru"
    # Cookie TTL for persistent chat sessions (seconds)
    session_ttl_seconds: int = 60 * 60 * 24 * 30  # 30 days

    # ── Ingestion ─────────────────────────────────────────────
    website_base_url: str = "https://lvtrade.ru"

    @property
    def allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.website_origins.split(",") if o.strip()]


settings = Settings()
