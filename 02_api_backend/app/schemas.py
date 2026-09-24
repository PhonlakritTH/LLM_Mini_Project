from typing import Literal, Optional
from pydantic import BaseModel, Field

UseCase = Literal["gaming", "video_editing", "office", "streaming", "ai_rendering"]
Brand = Literal["intel", "amd", "nvidia", "any"]

class ExistingPart(BaseModel):
    type: Literal["cpu", "motherboard", "ram", "gpu", "psu", "storage", "case"]
    name: str = Field(min_length=1, max_length=80)
    socket: Optional[str] = Field(default=None, max_length=20)
    wattage: Optional[int] = Field(default=None, ge=100, le=2000)

class BuildRequest(BaseModel):
    budget: int = Field(ge=8000, le=500000, description="THB")
    use_case: UseCase
    preferred_brand: Brand = "any"
    existing_parts: list[ExistingPart] = Field(default_factory=list, max_length=10)
    question: str = Field(default="", max_length=500)
    locale: str = "th-TH"
    request_id: str = Field(min_length=8, max_length=64)
    conversation_id: Optional[str] = Field(default=None, max_length=64)

class Part(BaseModel):
    type: str
    name: str
    price: int
    in_stock: Optional[bool] = None   # None = unknown (service degraded)
    source: str

class BuildResponse(BaseModel):
    recommendation_code: Literal["finalize_build", "swap_component", "wait_for_price_drop", "avoid_combination"]
    compatibility_status: Literal["compatible", "warning", "incompatible"]
    confidence: float
    summary: str
    reasons: list[str]
    conflicts: list[str] = []
    suggested_fix: Optional[str] = None
    parts_list: list[Part]
    price_breakdown: dict[str, int]
    benchmark_estimate: dict[str, float]
    sources: list[str]
    partial_result: bool = False
    degraded_services: list[str] = []
    updated_at: str
    request_id: str
    correlation_id: str
    conversation_id: str
