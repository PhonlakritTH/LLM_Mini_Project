from fastapi.testclient import TestClient
from app.main import app, _build_response
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
    assert result["recommendation_code"] == "wait_for_price_drop"
