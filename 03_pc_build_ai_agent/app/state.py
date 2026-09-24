import time
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field
from .config import settings

class BudgetExceeded(Exception):
    def __init__(self, kind: str): super().__init__(kind); self.kind = kind

class ExistingPart(BaseModel):
    type: Literal["cpu", "motherboard", "ram", "gpu", "psu", "storage", "case"]
    name: str = Field(max_length=80)
    socket: Optional[str] = None
    wattage: Optional[int] = None

class Constraints(BaseModel):
    max_wattage: Optional[int] = Field(default=None, ge=100, le=2000)
    case_form_factor: Optional[Literal["ITX", "mATX", "ATX"]] = None
    noise_level: Optional[Literal["quiet", "normal"]] = None

class AgentRequest(BaseModel):
    request_id: str
    conversation_id: Optional[str] = None
    budget: Optional[int] = Field(default=None, ge=0, le=500000)
    use_case: Optional[Literal["gaming", "video_editing", "office", "streaming", "ai_rendering"]] = None
    preferred_brand: Literal["intel", "amd", "nvidia", "any"] = "any"
    existing_parts: list[ExistingPart] = Field(default_factory=list, max_length=10)
    constraints: Constraints = Field(default_factory=Constraints)
    question: str = Field(default="", max_length=500)
    locale: str = "th-TH"

class AgentState(BaseModel):
    """Everything the agent knows. Serialisable for replay/regression tests."""
    request: AgentRequest
    intent: Optional[str] = None
    slots: dict[str, Any] = {}
    missing: list[str] = []
    assumptions: list[str] = []
    plan: list[str] = []
    parts: list[dict] = []
    observations: dict[str, Any] = {}
    data_quality: dict[str, Any] = {}
    compatibility: Optional[dict] = None
    evidence: list[dict] = []
    alternatives: list[dict] = []
    errors: list[str] = []
    degraded_services: list[str] = []
    needs_human_review: list[str] = []
    steps_used: int = 0
    tool_calls_used: int = 0
    deadline: float = 0.0
    trace: list[str] = []

    def start(self): self.deadline = time.monotonic() + settings.agent_total_timeout
    def time_left(self) -> float: return self.deadline - time.monotonic()
    def use_step(self, node: str):
        if self.steps_used >= settings.max_agent_steps: raise BudgetExceeded("steps")
        if self.time_left() <= 0: raise BudgetExceeded("time")
        self.steps_used += 1; self.trace.append(node)
    def use_tool(self):
        if self.tool_calls_used >= settings.max_tool_calls: raise BudgetExceeded("tool_calls")
        self.tool_calls_used += 1

    @property
    def remaining_budget(self) -> dict:
        return {"steps": settings.max_agent_steps - self.steps_used,
                "tool_calls": settings.max_tool_calls - self.tool_calls_used,
                "seconds": round(max(self.time_left(), 0), 2)}

class AgentResult(BaseModel):
    status: Literal["complete", "needs_info", "degraded", "budget_exhausted"]
    intent: Optional[str] = None
    questions: list[str] = []
    evidence_package: Optional[dict] = None
    errors: list[str] = []
    degraded_services: list[str] = []
    needs_human_review: list[str] = []
    remaining_budget: dict = {}
    trace: list[str] = []
    versions: dict[str, str] = {}
    request_id: str
    conversation_id: str
