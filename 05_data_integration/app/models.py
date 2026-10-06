from datetime import datetime, timezone
from typing import Literal, Optional
from pydantic import BaseModel

class RawRecord(BaseModel):
    """Normalized price-reference or component-spec evidence."""
    kind: Literal["price", "spec"]
    part_id: str
    source: str
    authority: Literal["manufacturer", "price_reference"] = "price_reference"
    fetched_at: str
    observed_at: str
    expires_at: str
    fields: dict

class QualityFlag(BaseModel):
    part_id: str
    flag: Literal["missing", "stale", "conflicting", "inferred"]
    detail: str

class PartRecord(BaseModel):
    part_id: str
    knowledge_id: Optional[str] = None
    category: str
    price: Optional[int] = None
    price_thb: Optional[int] = None
    price_low: Optional[int] = None
    price_high: Optional[int] = None
    performance_index: Optional[float] = None
    socket: Optional[str] = None
    chipset: Optional[str] = None
    form_factor: Optional[str] = None
    wattage_draw: Optional[int] = None
    performance_tier: Optional[str] = None
    compatibility_group: Optional[str] = None
    specs: dict = {}
    spec_sources: list[str] = []
    price_observed_at: Optional[str] = None
    price_source: Optional[str] = None
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
