from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class TenantOut(BaseModel):
    id: UUID
    slug: str
    name: str
    region: Literal["RU", "GLOBAL"]
    llm_provider: Literal["yandex", "claude"]
    brand_color: str
    logo_url: str | None
    language: str
    plan: str
    created_at: datetime
