import pytest
from jsonschema import ValidationError
from app.config import settings
from app.main import evaluate
from app.models import DecisionRequest

@pytest.fixture(autouse=True)
def live_llm_response(monkeypatch):
    async def call_llm(_prompt):
        return {"summary": "อธิบายจากหลักฐาน", "reasons": ["มีข้อมูลอ้างอิง"],
                "immediate_actions": []}
    monkeypatch.setattr("app.main.call_llm", call_llm)

def req(**k):
    base = dict(request_id="r1", budget=50000,
               parts=[{"price": 40000, "owned": False}],
               compatibility={"status": "COMPATIBLE", "score": 0.9, "uncertainty": 0.05, "hard_override": False, "reason_codes": []},
               alternatives={"options": []}, evidence={"passages": []})
    base.update(k); return DecisionRequest(**base)

async def test_finalize_when_all_good():
    r = await evaluate(req(), x_internal_token=settings.internal_token)
    assert r.action_code == "FINALIZE_BUILD" and r.compatibility_status == "compatible"
    assert r.llm_used and not r.fallback_used

async def test_avoid_when_incompatible_no_alternative():
    r = await evaluate(req(compatibility={"status": "INCOMPATIBLE", "score": 0.02, "uncertainty": 0.05, "hard_override": True, "reason_codes": ["socket_mismatch"]}),
                       x_internal_token=settings.internal_token)
    assert r.action_code == "AVOID_COMBINATION" and r.compatibility_status == "incompatible"

async def test_swap_when_incompatible_but_alternative_exists():
    r = await evaluate(req(compatibility={"status": "INCOMPATIBLE", "score": 0.02, "uncertainty": 0.05, "hard_override": True, "reason_codes": []},
                           alternatives={"options": [{"to_part": "x", "price_delta": -500, "value_score": 1.2}]}),
                       x_internal_token=settings.internal_token)
    assert r.action_code == "SWAP_COMPONENT"

async def test_over_budget_waits_without_alternative():
    r = await evaluate(req(budget=10000, parts=[{"price": 40000, "owned": False}]), x_internal_token=settings.internal_token)
    assert r.action_code == "RECONFIGURE_BUILD"

async def test_unknown_price_waits_without_reporting_zero_total():
    r = await evaluate(req(parts=[{"price": None, "owned": False}], degraded_services=["price"]),
                       x_internal_token=settings.internal_token)
    assert r.action_code == "NEEDS_PRICE_DATA"
    assert any("Reference price data is incomplete" in reason for reason in r.reasons)
    assert all("Total 0 THB" not in reason for reason in r.reasons)

async def test_median_price_within_budget_finalizes():
    r = await evaluate(req(budget=50000, parts=[{"price": 45000, "price_low": 42000, "price_high": 48000, "owned": False}],
                           data_quality={"total_price_range": {"low": 42000, "high": 48000}}),
                       x_internal_token=settings.internal_token)
    assert r.action_code == "FINALIZE_BUILD"
    assert r.compatibility_status == "compatible"

async def test_conflicting_prices_needs_review():
    r = await evaluate(req(budget=50000, parts=[{"price": 45000, "owned": False}],
                           data_quality={"flags": [{"flag": "conflicting"}]}),
                       x_internal_token=settings.internal_token)
    assert r.action_code == "NEEDS_REVIEW"


async def test_complete_prices_but_unverified_compatibility_needs_review_not_price_data():
    r = await evaluate(req(budget=50000, parts=[{"price": 40000, "owned": False}],
                           compatibility={"status": "NEEDS_REVIEW", "score": 0.6, "uncertainty": 0.2,
                                          "hard_override": False, "reason_codes": ["bios_unverified"]}),
                       x_internal_token=settings.internal_token)
    assert r.action_code == "NEEDS_REVIEW"
    assert "bios_unverified" in r.reasons[0]

async def test_incompatible_never_finalizes_even_with_weak_alternative_signal(monkeypatch):
    # monotonic safety: hard_override always blocks FINALIZE_BUILD regardless of anything else
    r = await evaluate(req(compatibility={"status": "INCOMPATIBLE", "score": 0.99, "uncertainty": 0.0, "hard_override": True, "reason_codes": []}),
                       x_internal_token=settings.internal_token)
    assert r.action_code != "FINALIZE_BUILD"

async def test_missing_evidence_lowers_confidence_and_escalates():
    r = await evaluate(req(degraded_services=["price"]), x_internal_token=settings.internal_token)
    assert r.escalate and r.confidence < 0.9

async def test_llm_tampering_with_action_code_is_rejected():
    from app.explainer import validate_and_lock
    with pytest.raises(ValidationError):
        validate_and_lock({"action_code": "FINALIZE_BUILD", "summary": "x", "reasons": [], "immediate_actions": []}, [], None)

async def test_missing_llm_key_returns_an_explicit_provider_error(monkeypatch):
    from app import main
    from fastapi import HTTPException
    from app.explainer import call_llm
    monkeypatch.setattr(main, "call_llm", call_llm)
    monkeypatch.setattr(settings, "llm_api_key", "")
    with pytest.raises(HTTPException) as error:
        await evaluate(req(), x_internal_token=settings.internal_token)
    assert error.value.status_code == 503
    assert "LLM_API_KEY is not configured" in error.value.detail

async def test_openai_compatible_provider_returns_validated_json(monkeypatch):
    import httpx
    from app.explainer import call_llm
    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    monkeypatch.setattr(settings, "llm_base_url", "https://llm.example/v1")

    class Response:
        def raise_for_status(self): pass
        def json(self):
            return {"choices": [{"message": {"content":
                '{"summary":"ok","reasons":["evidence"],"immediate_actions":[]}'}}]}

    class Client:
        def __init__(self, **_kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *_args): pass
        async def post(self, url, headers, json):
            assert url == "https://llm.example/v1/chat/completions"
            assert headers["Authorization"] == "Bearer test-key"
            assert json["response_format"] == {"type": "json_object"}
            return Response()

    monkeypatch.setattr(httpx, "AsyncClient", Client)
    result = await call_llm('{"locked_action":"NEEDS_REVIEW"}')
    assert result["summary"] == "ok"


@pytest.mark.parametrize(("status", "message"), [
    (401, "Verify LLM_API_KEY"),
    (403, "permissions, model access, and billing"),
    (404, "LLM_BASE_URL and LLM_MODEL_EXPLAINER"),
    (429, "quota or rate limit"),
])
async def test_provider_http_errors_return_actionable_messages(monkeypatch, status, message):
    import httpx
    from app.explainer import LLMProviderError, call_llm
    monkeypatch.setattr(settings, "llm_api_key", "test-key")

    class Response:
        status_code = status
        request = httpx.Request("POST", "https://llm.example/v1/chat/completions")

        def raise_for_status(self):
            raise httpx.HTTPStatusError("provider failure", request=self.request, response=httpx.Response(
                status, request=self.request,
            ))

    class Client:
        def __init__(self, **_kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *_args): pass
        async def post(self, *_args, **_kwargs): return Response()

    monkeypatch.setattr(httpx, "AsyncClient", Client)
    with pytest.raises(LLMProviderError, match=message):
        await call_llm("test")

async def test_unsupported_locale_rejected():
    with pytest.raises(Exception):
        await evaluate(req(locale="fr-FR"), x_internal_token=settings.internal_token)
