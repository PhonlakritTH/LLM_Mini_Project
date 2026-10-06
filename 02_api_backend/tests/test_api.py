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

def test_fallback_response_has_real_store_search_links_not_mock_offers():
    request = BuildRequest(**body())
    result = _build_response({"status": "complete", "degraded_services": [], "evidence_package": {
        "parts": [{"type": "cpu", "name": "AMD Ryzen 5 7600", "price": None,
                   "price_low": None, "price_high": None, "owned": False}],
        "compatibility": {"status": "NEEDS_REVIEW", "conflicts": [], "warnings": [],
                          "unknown": ["BIOS version is not verified"]},
        "data_quality": {"total_price": None}, "alternatives": [], "sources": [],
        "updated_at": "2026-10-06T00:00:00Z"
    }}, request)

    links = result["parts_list"][0]["store_search_links"]
    assert [link["store"] for link in links] == ["BaNANA", "Amazon.com"]
    assert all("AMD+Ryzen+5+7600" in link["url"] for link in links)
    assert all("price" not in link and "stock" not in link for link in links)

def test_complete_price_range_with_unverified_compatibility_is_not_reported_as_missing_price():
    request = BuildRequest(**body())
    result = _build_response({"status": "degraded", "degraded_services": [], "evidence_package": {
        "parts": [{"type": "cpu", "name": "CPU A", "price": 40000,
                   "price_low": 35000, "price_high": 45000, "owned": False}],
        "compatibility": {"status": "warning", "conflicts": [], "warnings": [],
                          "unknown": ["BIOS support has not been verified"]},
        "data_quality": {"total_price": 40000,
                         "total_price_range": {"low": 35000, "high": 45000}},
        "alternatives": [], "sources": [], "updated_at": "2026-10-06T00:00:00Z"
    }}, request)

    assert result["recommendation_code"] == "needs_review"
    assert result["data_quality"]["total_price_range"] == {"low": 35000, "high": 45000}
    assert "ราคาอ้างอิงแล้ว" in result["summary"]

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
                    "reason_codes": ["unknown_socket_data"], "evidence_sources": ["https://vendor.example/support"],
                    "hard_override": False},
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
    assert "https://vendor.example/support" in result["sources"]

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

@pytest.mark.asyncio
async def test_missing_live_decision_service_returns_error_not_a_template(monkeypatch):
    from app import main
    from app.main import ApiError

    async def post_service(_base, path, _payload):
        if path == "/v1/integration/snapshot":
            return {"parts": [], "data_quality": {"coverage": 1, "freshness_ok": True, "flags": []}}
        if path == "/v1/knowledge/assess":
            return {"compatibility": {"status": "COMPATIBLE", "score": 1, "uncertainty": 0,
                                      "reason_codes": [], "hard_override": False},
                    "alternatives": {"options": []}, "evidence": {"passages": []},
                    "degraded_services": []}
        return None

    monkeypatch.setattr(main, "_post_service", post_service)
    agent = {"status": "complete", "degraded_services": [],
             "evidence_package": {"parts": [], "records": [], "sources": [],
                                  "data_quality": {}, "request_summary": {}}}
    with pytest.raises(ApiError) as error:
        await _orchestrate(agent, BuildRequest(**body()))
    assert error.value.status == 503
    assert error.value.code == "DECISION_ENGINE_UNAVAILABLE"


@pytest.mark.asyncio
async def test_decision_provider_error_is_reported_to_the_user(monkeypatch):
    import httpx
    from app import main
    from app.main import ApiError

    class Response:
        is_error = True
        status_code = 503

        def json(self):
            return {"detail": "LLM provider rejected the API key (HTTP 401)."}

    class Client:
        def __init__(self, **_kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *_args): pass
        async def post(self, *_args, **_kwargs): return Response()

    monkeypatch.setattr(httpx, "AsyncClient", Client)
    with pytest.raises(ApiError) as error:
        await main._post_service("http://decision-llm:8500", "/v1/decision/evaluate", {})
    assert error.value.code == "LLM_PROVIDER_ERROR"
    assert "HTTP 401" in error.value.msg
