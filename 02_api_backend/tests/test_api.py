import pytest
from fastapi.testclient import TestClient
from app.main import app, _build_response, _orchestrate
from app.schemas import BuildRequest
c = TestClient(app)
def hdr(): return {"Authorization": "Bearer " + c.post("/v1/auth/dev-token").json()["access_token"]}
def body(**k): return {"budget": 50000, "use_case": "gaming", "request_id": "req-12345678", **k}
def test_requires_auth(): assert c.post("/v1/builder/recommendations", json=body()).status_code == 401
def test_invalid_budget(): assert c.post("/v1/builder/recommendations", json=body(budget=10), headers=hdr()).status_code == 422
def test_agent_unavailable_is_not_replaced_by_stub(monkeypatch):
    from app import main
    monkeypatch.setattr(main.s, "agent_service_url", "http://127.0.0.1:1")
    r = c.post("/v1/builder/recommendations", headers=hdr(), json=body())
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "RECOMMENDER_UNAVAILABLE"

def test_incompatible_agent_result_maps_to_avoid():
    request = BuildRequest(**body())
    result = _build_response({"status": "complete", "degraded_services": [], "evidence_package": {
        "parts": [], "compatibility": {"status": "incompatible", "conflicts": ["Socket mismatch"], "warnings": [], "unknown": []},
        "data_quality": {"total_price": 10000}, "sources": [], "updated_at": "2026-10-03T00:00:00Z"
    }}, request)
    assert result["recommendation_code"] == "avoid_combination"
    assert result["compatibility_status"] == "incompatible"

def test_over_budget_without_alternative_does_not_claim_a_swap():
    request = BuildRequest(**body(budget=10000))
    result = _build_response({"status": "complete", "degraded_services": [], "evidence_package": {
        "parts": [], "compatibility": {"status": "compatible", "conflicts": [], "warnings": [], "unknown": []},
        "data_quality": {"total_price": 20000}, "alternatives": [], "sources": [],
        "updated_at": "2026-10-03T00:00:00Z"
    }}, request)
    assert result["recommendation_code"] == "reconfigure_build"

@pytest.mark.asyncio
async def test_orchestration_keeps_unknown_price_degraded_through_modules_05_to_08(monkeypatch):
    from app import main
    calls = []
    output_part = {"type": "cpu", "name": "CPU A", "price": None,
                   "price_low": None, "price_high": None, "owned": False}

    async def post_service(_base, path, payload):
        calls.append((path, payload))
        if path == "/v1/integration/snapshot":
            assert payload["requested_parts"][0]["part_id"] == "CPU A"
            return {"parts": [{"part_id": "CPU A", "category": "cpu", "price": None,
                               "owned": False, "degraded": True}],
                    "data_quality": {"coverage": 0.0, "freshness_ok": True, "flags": []}}
        if path == "/v1/knowledge/assess":
            return {"compatibility": {"status": "NEEDS_REVIEW", "score": 0.5, "uncertainty": 0.4,
                    "reason_codes": ["unknown_socket_data"], "hard_override": False},
                    "alternatives": {"options": []}, "evidence": {"passages": []},
                    "degraded_services": ["rag_provider_unavailable", "alternatives_provider_unavailable"]}
        if path == "/v1/decision/evaluate":
            assert "price" in payload["degraded_services"]
            return {"action_code": "NEEDS_PRICE_DATA", "compatibility_status": "warning", "confidence": 0.3,
                    "escalate": True, "summary": "ข้อมูลไม่ครบ", "reasons": ["ราคาไม่ทราบ"],
                    "immediate_actions": [], "citations": [], "versions": {}, "conversation_id": "c1"}
        return {"action_code": "NEEDS_PRICE_DATA", "compatibility_status": "warning", "confidence": 0.3,
                "short_summary": "ข้อมูลไม่ครบ", "primary_build": [output_part], "reasons": ["ราคาไม่ทราบ"],
                "immediate_actions": [], "sources": [], "fetched_at": "2026-10-05T00:00:00Z"}

    monkeypatch.setattr(main, "_post_service", post_service)
    request = BuildRequest(**body())
    agent = {"status": "degraded", "degraded_services": ["price", "stock", "benchmark"],
             "evidence_package": {"parts": [{"type": "cpu", "name": "CPU A", "owned": False}],
                                 "records": [], "sources": [], "data_quality": {}, "request_summary": {}}}
    result = await _orchestrate(agent, request)

    assert [path for path, _ in calls] == ["/v1/integration/snapshot", "/v1/knowledge/assess",
                                          "/v1/decision/evaluate", "/v1/recommendation/build"]
    assert result["status"] == "degraded" and result["partial_result"]
    assert result["recommendation_code"] == "needs_price_data"
    assert result["parts_list"][0]["price"] is None

@pytest.mark.asyncio
async def test_downstream_failure_never_finalizes_build(monkeypatch):
    from app import main
    async def unavailable(*_args, **_kwargs): return None
    monkeypatch.setattr(main, "_post_service", unavailable)
    request = BuildRequest(**body())
    agent = {"status": "complete", "degraded_services": [], "evidence_package": {
        "parts": [{"type": "cpu", "name": "CPU A", "price": 1000, "owned": False}],
        "data_quality": {"total_price": 1000}, "compatibility": {"status": "compatible"}, "sources": []}}
    result = await _orchestrate(agent, request)
    assert result["status"] == "degraded"
    assert result["recommendation_code"] != "finalize_build"
    assert "data_integration" in result["degraded_services"]
