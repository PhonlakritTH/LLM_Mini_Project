from datetime import datetime, timezone
from typing import Literal, Optional
from pydantic import BaseModel


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class PriceListing(BaseModel):
    part_id: str
    currency: Literal["THB"] = "THB"
    price: int
    low_price: int
    high_price: int
    observation_count: int
    source: str
    fetched_at: str
    observed_at: str
    expires_at: str


class ProviderHealth(BaseModel):
    provider: str
    healthy: bool
    latency_ms: float
    breaker_open: bool
    last_error: Optional[str] = None


class DataQuality(BaseModel):
    coverage: float
    freshness_ok: bool
    disagreement: list[str] = []


class QueryRequest(BaseModel):
    part_ids: list[str]
    category: Optional[str] = None
    budget_range: Optional[tuple[int, int]] = None
    brand: Optional[str] = None
    search_terms: dict[str, list[str]] = {}
    fields: list[Literal["price"]] = ["price"]
    locale: str = "th-TH"


class QueryResponse(BaseModel):
    prices: list[PriceListing] = []
    provider_health: list[ProviderHealth] = []
    data_quality: DataQuality
    degraded: bool = False
