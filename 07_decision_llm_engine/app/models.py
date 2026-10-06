from typing import Literal, Optional
from pydantic import BaseModel

ActionCode = Literal["FINALIZE_BUILD", "SWAP_COMPONENT", "RECONFIGURE_BUILD", "NEEDS_PRICE_DATA", "AVOID_COMBINATION"]

class DecisionRequest(BaseModel):
    request_id: str
    conversation_id: Optional[str] = None
    budget: int
    parts: list[dict]                 # PartRecord-like dicts from module 05
    compatibility: dict                # CompatibilityAssessment from module 06
    alternatives: dict                 # AlternativeBuildOptions from module 06
    evidence: dict                     # RetrievedEvidence from module 06
    data_quality: dict = {}
    degraded_services: list[str] = []
    locale: str = "th-TH"

class Citation(BaseModel):
    document_id: str
    section: str

class DecisionResult(BaseModel):
    action_code: ActionCode
    compatibility_status: Literal["compatible", "warning", "incompatible"]
    confidence: float
    escalate: bool
    rules_fired: list[str]
    summary: str
    reasons: list[str]
    immediate_actions: list[str]
    citations: list[Citation]
    llm_used: bool
    fallback_used: bool
    request_id: str
    conversation_id: str
    versions: dict[str, str]
    audit_trace: list[str]
