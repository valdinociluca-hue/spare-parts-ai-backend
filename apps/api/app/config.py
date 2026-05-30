from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    environment: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"
    app_secret_key: str = "replace-me-in-prod"
    jwt_secret: str = "replace-me-in-prod"

    database_url: str = (
        "postgresql://postgres:postgres@localhost:54322/postgres"
    )
    db_pool_min_size: int = 1
    db_pool_max_size: int = 10

    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    pinecone_api_key: str = ""
    pinecone_index: str = "partsai-products"
    pinecone_environment: str = "us-east-1"

    yandex_api_key: str = ""
    yandex_folder_id: str = ""
    yandex_gpt_model: str = "yandexgpt"
    yandex_api_base: str = "https://llm.api.cloud.yandex.net"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"

    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"
    openai_embedding_dim: int = 1536

    llm_temperature: float = 0.1
    llm_max_tokens: int = 1500
    llm_timeout: float = 45.0

    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:3001",
        ]
    )

    @property
    def use_stub_llm(self) -> bool:
        """If no provider keys are set, fall back to a deterministic stub."""
        return not self.yandex_api_key and not self.anthropic_api_key


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
