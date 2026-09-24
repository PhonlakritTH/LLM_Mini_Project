import pytest
from app.config import settings
from app.graph import run_agent, CHECKPOINTS
from app.state import AgentRequest
from app import tools

@pytest.fixture(autouse=True)
def reset(monkeypatch):
    tools.reset_breakers(); CHECKPOINTS.clear()
    monkeypatch.setattr(settings, "retry_base_delay", 0); monkeypatch.setattr(settings, "mock_fail", "")

def req(**k): return AgentRequest(request_id="req-12345678", budget=60000, use_case="gaming", **k)

async def test_happy_path():
    r = await run_agent(req())
    assert r.status == "complete" and r.evidence_package["compatibility"]["status"] == "compatible"
    assert r.evidence_package["data_quality"]["evidence_complete"] and r.remaining_budget["tool_calls"] >= 0

async def test_asks_for_missing_budget():
    r = await run_agent(AgentRequest(request_id="req-12345678", use_case="gaming"))
    assert r.status == "needs_info" and "budget" in r.questions[0].lower() and r.evidence_package is None

async def test_degraded_when_stock_down(monkeypatch):
    monkeypatch.setattr(settings, "mock_fail", "stock")
    r = await run_agent(req())
    assert r.status == "degraded" and r.degraded_services == ["stock"]
    assert r.evidence_package["parts"][0]["in_stock"] is None

async def test_socket_conflict():
    r = await run_agent(req(preferred_brand="amd", existing_parts=[{"type": "motherboard", "name": "Z690", "socket": "LGA1700"}]))
    assert r.evidence_package["compatibility"]["status"] == "incompatible"

async def test_unknown_socket_escalates_to_human():
    r = await run_agent(req(existing_parts=[{"type": "motherboard", "name": "MysteryBoard"}]))
    assert r.needs_human_review and r.status == "degraded"

async def test_tool_budget_stops_agent(monkeypatch):
    monkeypatch.setattr(settings, "max_tool_calls", 1)
    r = await run_agent(req())
    assert r.status == "budget_exhausted"

async def test_step_budget(monkeypatch):
    monkeypatch.setattr(settings, "max_agent_steps", 2)
    assert (await run_agent(req())).status == "budget_exhausted"

async def test_unknown_tool_denied():
    from app.state import AgentState
    s = AgentState(request=req()); s.start()
    with pytest.raises(tools.ToolDenied): await tools.call_tool(s, "shell", {})

async def test_followup_reuses_checkpoint():
    await run_agent(req(conversation_id="c1"))
    r = await run_agent(AgentRequest(request_id="req-87654321", conversation_id="c1", question="ขอถูกลงหน่อย"))
    assert r.intent == "continue" and r.status in ("complete", "degraded")
