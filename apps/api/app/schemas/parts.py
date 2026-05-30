from pydantic import BaseModel, Field


class IdentifyContext(BaseModel):
    client_id: str | None = None
    equipment_model: str | None = None


class IdentifyRequest(BaseModel):
    session_token: str
    query: str = Field(min_length=1)
    context: IdentifyContext = Field(default_factory=IdentifyContext)


class ProductMatch(BaseModel):
    sku: str
    name: str
    brand: str | None = None
    manufacturer_part_number: str | None = None
    score: float
    stock: float
    price: float | None
    currency: str
    image_url: str | None = None
    reasoning: str = ""


class TokenUsage(BaseModel):
    provider: str
    model: str
    tokens_used: int


class IdentifyResponse(BaseModel):
    matches: list[ProductMatch]
    usage: TokenUsage


class SearchFilters(BaseModel):
    brand: str | None = None
    category: str | None = None
    in_stock: bool | None = None


class SearchRequest(BaseModel):
    query: str
    filters: SearchFilters = Field(default_factory=SearchFilters)


class SearchResponse(BaseModel):
    products: list[ProductMatch]
