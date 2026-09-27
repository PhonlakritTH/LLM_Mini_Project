from typing import Literal, Optional
from pydantic import BaseModel

class CompatibilityAssessment(BaseModel):
    status: Literal["COMPATIBLE", "NEEDS_REVIEW", "INCOMPATIBLE"]
    score: float                       # model probability of compatibility
    uncertainty: float
    reason_codes: list[str]
    hard_override: bool                # a rule fired regardless of model score
    model_version: str
    feature_schema_version: str

class EvidencePassage(BaseModel):
    document_id: str
    title: str
    page: int
    section: str
    snippet: str
    authority: Literal["manufacturer", "retailer"]
    effective_date: str
    score: float

class RetrievedEvidence(BaseModel):
    query: str
    passages: list[EvidencePassage]
    found: bool
    confidence: float
    collection_version: str

class AlternativeOption(BaseModel):
    swap_type: str
    from_part: str
    to_part: str
    price_delta: int
    performance_delta: float
    value_score: float
    hops: int
    freshness: str

class AlternativeBuildOptions(BaseModel):
    options: list[AlternativeOption]
    excluded: list[str]   # names filtered out with a short reason

class KnowledgeRequest(BaseModel):
    request_id: str
    snapshot: dict           # PartCatalogSnapshot.model_dump() from module 05
    existing_parts: list[dict] = []
    constraints: dict = {}
    question: str = ""
    locale: str = "th-TH"
    budget: Optional[int] = None

class KnowledgeResponse(BaseModel):
    compatibility: CompatibilityAssessment
    evidence: RetrievedEvidence
    alternatives: AlternativeBuildOptions
    degraded: bool
    degraded_services: list[str] = []
    versions: dict[str, str]
