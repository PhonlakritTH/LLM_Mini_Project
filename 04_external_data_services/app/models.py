from datetime import datetime, timezone
from typing import Literal, Optional
from pydantic import BaseModel

def now_iso() -> str: return datetime.now(timezone.utc).isoformat()

class Provenance(BaseModel):
    source: str
    fetched_at: str      # when we pulled it (ingestion time)
    observed_at: str     # when the provider says the value was true (event time)
    expires_at: str
    schema_version: str = "1.0"

class PriceListing(Provenance):
    part_id: str
    retailer: str
    currency: Literal["THB"] = "THB"
    price: int
    discount_pct: float = 0.0
    bundle_note: Optional[str] = None

class StockStatus(Provenance):
    part_id: str
    retailer: str
    in_stock: bool
    restock_estimate: Optional[str] = None
    warehouse: Optional[str] = None

class BenchmarkScore(Provenance):
    part_id: str
    cinebench: Optional[float] = None
    passmark: Optional[float] = None
    threedmark: Optional[float] = None
    game_fps_1080p: Optional[float] = None
    performance_index: float   # common 0-100 scale, derived from the above

class SpecRecord(Provenance):
    part_id: str
    socket: Optional[str] = None
    chipset: Optional[str] = None
    form_factor: Optional[str] = None
    wattage_draw: Optional[int] = None
    authority: Literal["manufacturer", "retailer"] = "retailer"

class ProviderHealth(BaseModel):
    provider: str
    healthy: bool
    latency_ms: float
    breaker_open: bool
    last_error: Optional[str] = None

class DataQuality(BaseModel):
    coverage: float          # fraction of requested parts returned
    freshness_ok: bool
    disagreement: list[str] = []   # part_ids where sources disagree materially

class QueryRequest(BaseModel):
    part_ids: list[str]
    category: Optional[str] = None
    budget_range: Optional[tuple[int, int]] = None
    brand: Optional[str] = None
    fields: list[Literal["price", "stock", "benchmark", "spec"]] = ["price", "stock", "benchmark", "spec"]
    locale: str = "th-TH"

class QueryResponse(BaseModel):
    prices: list[PriceListing] = []
    stock: list[StockStatus] = []
    benchmarks: list[BenchmarkScore] = []
    specs: list[SpecRecord] = []
    provider_health: list[ProviderHealth] = []
    data_quality: DataQuality
    degraded: bool = False
