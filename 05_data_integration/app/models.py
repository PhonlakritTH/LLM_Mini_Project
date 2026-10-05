from datetime import datetime, timezone
from typing import Literal, Optional
from pydantic import BaseModel

class RawRecord(BaseModel):
    """What module 04 sends: one of price/stock/benchmark/spec, already canonical-shaped but unvalidated as a set."""
    kind: Literal["price", "stock", "benchmark", "spec"]
    part_id: str
    source: str
    authority: Literal["manufacturer", "retailer"] = "retailer"
    fetched_at: str
    observed_at: str
    expires_at: str
    fields: dict

class QualityFlag(BaseModel):
    part_id: str
    flag: Literal["missing", "stale", "conflicting", "inferred", "out_of_stock"]
    detail: str

class PartRecord(BaseModel):
    part_id: str
    category: str
    price: Optional[int] = None
    price_thb: Optional[int] = None
    in_stock: Optional[bool] = None
    performance_index: Optional[float] = None
    socket: Optional[str] = None
    chipset: Optional[str] = None
    form_factor: Optional[str] = None
    wattage_draw: Optional[int] = None
    performance_tier: Optional[str] = None
    compatibility_group: Optional[str] = None
    owned: bool = False
    degraded: bool = False
    lineage: dict[str, list[str]] = {}   # field -> list of source ids that contributed

class DataQualitySummary(BaseModel):
    coverage: float
    freshness_ok: bool
    completeness: float
    quality_score: float
    flags: list[QualityFlag] = []

class PartCatalogSnapshot(BaseModel):
    snapshot_id: str
    schema_version: str
    currency: str
    request_id: str
    budget: Optional[int] = None
    use_case: Optional[str] = None
    parts: list[PartRecord]
    quarantined: list[dict] = []
    data_quality: DataQualitySummary
    created_at: str

class IntegrationRequest(BaseModel):
    request_id: str
    budget: Optional[int] = None
    use_case: Optional[str] = None
    existing_parts: list[dict] = []
    requested_parts: list[dict] = []
    records: list[RawRecord] = []
