import pytest
from app.config import settings
from app.graph import run_agent, CHECKPOINTS
from app.state import AgentRequest
from app import tools

@pytest.fixture(autouse=True)
def reset(monkeypatch):
    tools.reset_breakers(); CHECKPOINTS.clear()
    monkeypatch.setattr(settings, "retry_base_delay", 0)

def req(**k):
    values = {"request_id": "req-12345678", "budget": 60000, "use_case": "gaming"}
    values.update(k)
    return AgentRequest(**values)

async def test_unconfigured_providers_return_degraded_without_fabricated_evidence():
    r = await run_agent(req())
    assert r.status == "degraded"
    assert r.degraded_services == ["price"]
    assert not r.evidence_package["data_quality"]["evidence_complete"]
    assert all(part["price"] is None for part in r.evidence_package["parts"] if not part["owned"])
    assert all(part["spec_source"] for part in r.evidence_package["parts"])
    assert next(part for part in r.evidence_package["parts"] if part["type"] == "cpu")["name"] == "AMD Ryzen 5 7600"
    assert next(part for part in r.evidence_package["parts"] if part["type"] == "gpu")["brand"] == "nvidia"

async def test_asks_for_missing_budget():
    r = await run_agent(AgentRequest(request_id="req-12345678", use_case="gaming"))
    assert r.status == "needs_info" and "budget" in r.questions[0].lower() and r.evidence_package is None

async def test_stock_is_not_part_of_the_build_flow():
    r = await run_agent(req())
    assert r.status == "degraded" and "stock" not in r.degraded_services
    assert all("in_stock" not in part for part in r.evidence_package["parts"])

async def test_price_tool_normalizes_reference_range_and_provenance(monkeypatch):
    from app.state import AgentState

    class Response:
        status_code = 200
        def json(self):
            return {"provider_health": [{"healthy": True}], "prices": [{
                "part_id": "Ryzen 5 7600", "price": 7590, "source": "serpapi_google_shopping",
                "fetched_at": "2026-10-03T00:00:00Z", "observed_at": "2026-10-03T00:00:00Z",
                "expires_at": "2026-10-03T00:02:00Z", "low_price": 7000, "high_price": 8000,
                "observation_count": 4
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
    result = await tools.call_tool(state, "price", {"names": ["Ryzen 5 7600", "RTX 4060"],
        "search_terms": {"Ryzen 5 7600": ["amd", "ryzen", "7600"], "RTX 4060": ["msi", "rtx", "4060"]}})
    assert result["prices"] == {"Ryzen 5 7600": 7590}
    assert result["missing"] == ["RTX 4060"]
    assert result["ranges"]["Ryzen 5 7600"] == (7000, 8000)
    assert result["records"][0]["observed_at"] == "2026-10-03T00:00:00Z"

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
    monkeypatch.setattr(settings, "max_tool_calls", 0)
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

async def test_budget_selects_best_affordable_sourced_component_combination(monkeypatch):
    from app import graph

    async def prices(_state, _name, payload):
        ranges = {}
        for name in payload["names"]:
            if "5600" in name:
                value = 5000
            elif "7600" in name and "RX" not in name:
                value = 8000
            elif "12400" in name:
                value = 6000
            elif "B550M" in name:
                value = 4000
            elif "B650M" in name:
                value = 7000
            elif "B760M" in name:
                value = 5000
            elif "DDR4" in name:
                value = 2000
            elif "DDR5" in name:
                value = 3000
            elif "RTX 4060" in name:
                value = 12000
            elif "RX 7600" in name:
                value = 10000
            else:
                value = 2000
            ranges[name] = (value, value + 500)
        return {"prices": {name: (low + high) // 2 for name, (low, high) in ranges.items()},
                "ranges": ranges, "missing": [], "as_of": "2026-10-06T00:00:00+00:00",
                "source": "Google Shopping via SerpApi", "records": []}

    monkeypatch.setattr(graph, "call_tool", prices)
    result = await run_agent(req(budget=32000))
    assert result.evidence_package["data_quality"]["budget_fit"] == "within_budget"
    assert result.evidence_package["data_quality"]["total_price_range"]["high"] <= 32000
    assert any(part["name"] == "AMD Ryzen 5 5600" for part in result.evidence_package["parts"])
    assert all(part.get("spec_source") for part in result.evidence_package["parts"])


async def test_unsupported_requested_model_is_not_invented():
    result = await run_agent(req(preferred_cpu_model="Ryzen 7 9999"))
    assert result.status == "needs_info"
    assert result.evidence_package is None

def test_knowledge_seed_is_loaded_into_sqlite():
    from app.knowledge_base import BY_TYPE, MODULE_ROOT, settings as knowledge_settings
    from pathlib import Path

    database = Path(knowledge_settings.knowledge_database_path)
    if not database.is_absolute():
        database = MODULE_ROOT / database
    assert database.is_file()
    assert len(BY_TYPE["cpu"]) == 3
    assert all(part["source"].startswith("https://") for part in BY_TYPE["cpu"])
