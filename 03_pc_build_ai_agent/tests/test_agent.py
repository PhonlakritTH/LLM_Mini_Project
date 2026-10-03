import pytest
from app.config import settings
from app.graph import run_agent, CHECKPOINTS
from app.state import AgentRequest
from app import tools

@pytest.fixture(autouse=True)
def reset(monkeypatch):
    tools.reset_breakers(); CHECKPOINTS.clear()
    monkeypatch.setattr(settings, "retry_base_delay", 0)

def req(**k): return AgentRequest(request_id="req-12345678", budget=60000, use_case="gaming", **k)

async def test_unconfigured_providers_return_degraded_without_fabricated_evidence():
    r = await run_agent(req())
    assert r.status == "degraded"
    assert {"price", "stock", "benchmark", "knowledge_services"}.issubset(r.degraded_services)
    assert not r.evidence_package["data_quality"]["evidence_complete"]
    assert all(part["price"] is None for part in r.evidence_package["parts"] if not part["owned"])

async def test_asks_for_missing_budget():
    r = await run_agent(AgentRequest(request_id="req-12345678", use_case="gaming"))
    assert r.status == "needs_info" and "budget" in r.questions[0].lower() and r.evidence_package is None

async def test_unconfigured_services_are_reported_degraded(monkeypatch):
    monkeypatch.setattr(settings, "stock_service_url", "")
    r = await run_agent(req())
    assert r.status == "degraded" and "stock" in r.degraded_services
    assert r.evidence_package["parts"][0]["in_stock"] is None

async def test_price_tool_normalizes_external_query_and_retailer_link(monkeypatch):
    from app.state import AgentState

    class Response:
        status_code = 200
        def json(self):
            return {"provider_health": [{"healthy": True}], "prices": [{
                "part_id": "Ryzen 5 7600", "price": 7590, "source": "serpapi_google_shopping",
                "fetched_at": "2026-10-03T00:00:00Z", "product_url": "https://shop.example/item"
            }]}
        def raise_for_status(self): pass

    class Client:
        def __init__(self, **_kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *_args): pass
        async def post(self, url, json, headers):
            assert url.endswith("/v1/external/query")
            assert headers["X-Internal-Token"] == settings.internal_token
            assert json["fields"] == ["price"]
            return Response()

    monkeypatch.setattr(settings, "price_service_url", "http://external-data:8200")
    monkeypatch.setattr(tools.httpx, "AsyncClient", Client)
    state = AgentState(request=req())
    state.start()
    result = await tools.call_tool(state, "price", {"names": ["Ryzen 5 7600", "RTX 4060"]})
    assert result["prices"] == {"Ryzen 5 7600": 7590}
    assert result["missing"] == ["RTX 4060"]
    assert result["links"]["Ryzen 5 7600"] == "https://shop.example/item"

async def test_socket_conflict():
    r = await run_agent(req(preferred_brand="amd", existing_parts=[{"type": "motherboard", "name": "Z690", "socket": "LGA1700"}]))
    assert r.evidence_package["compatibility"]["status"] == "incompatible"

async def test_unknown_socket_escalates_to_human():
    r = await run_agent(req(existing_parts=[{"type": "motherboard", "name": "MysteryBoard"}]))
    assert r.needs_human_review and r.status == "degraded"

async def test_unknown_owned_psu_wattage_requires_human_review():
    r = await run_agent(req(existing_parts=[{"type": "psu", "name": "Unknown PSU"}]))
    assert r.needs_human_review and any("Wattage" in reason for reason in r.needs_human_review)

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
