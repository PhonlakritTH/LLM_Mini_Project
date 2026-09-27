import hashlib
from datetime import datetime, timezone
from typing import Literal, Optional
from pydantic import BaseModel

def now_iso(): return datetime.now(timezone.utc).isoformat()
def pseudonymize(user_id: str) -> str: return hashlib.sha256(f"pcb-salt-{user_id}".encode()).hexdigest()[:20]

class PartLine(BaseModel):
    type: str
    name: str
    price: int
    in_stock: Optional[bool] = None

class AlternativeLine(BaseModel):
    to_part: str
    price_delta: int
    performance_delta: float

class SourceLine(BaseModel):
    document_id: str
    section: str

class WarrantyContact(BaseModel):
    manufacturer: str
    region: str
    phone: str
    effective_date: str

class FormatRequest(BaseModel):
    request_id: str
    conversation_id: str
    user_id: Optional[str] = None
    locale: str = "th-TH"
    action_code: Literal["FINALIZE_BUILD", "SWAP_COMPONENT", "WAIT_FOR_PRICE_DROP", "AVOID_COMBINATION"]
    compatibility_status: Literal["compatible", "warning", "incompatible"]
    confidence: float
    escalate: bool
    summary: str
    reasons: list[str]
    immediate_actions: list[str]
    citations: list[SourceLine]
    parts: list[PartLine]
    alternatives: list[AlternativeLine] = []
    degraded_services: list[str] = []
    price_observed_at: Optional[str] = None
    consent_live_updates: bool = False
    versions: dict[str, str] = {}

class RecommendationResponse(BaseModel):
    schema_version: str
    request_id: str
    conversation_id: str
    action_code: str
    compatibility_status: str
    confidence: float
    short_summary: str
    immediate_actions: list[str]
    primary_build: list[PartLine]
    alternatives: list[AlternativeLine]
    setup_instructions: list[str]
    manufacturer_support_contacts: list[WarrantyContact]
    reasons: list[str]
    sources: list[SourceLine]
    observed_at: Optional[str]
    fetched_at: str
    expires_at: str
    limitations: list[str]
    degraded_services: list[str]
    live_updates_enabled: bool
    versions: dict[str, str]

class Feedback(BaseModel):
    request_id: str
    user_id: str
    category: Literal["helpful", "incorrect", "stale", "unsafe", "price_issue", "source_issue"]
    comment: str = ""

class FeedbackReceipt(BaseModel):
    feedback_id: str
    pseudonymous_id: str
    stored_at: str
    routed_to_safety_review: bool
