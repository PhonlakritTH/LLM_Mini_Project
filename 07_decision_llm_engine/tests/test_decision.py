import pytest
from app.config import settings
from app.main import evaluate
from app.models import DecisionRequest

def req(**k):
    base = dict(request_id="r1", budget=50000,
               parts=[{"price": 40000, "in_stock": True}],
               compatibility={"status": "COMPATIBLE", "score": 0.9, "uncertainty": 0.05, "hard_override": False, "reason_codes": []},
               alternatives={"options": []}, evidence={"passages": []})
    base.update(k); return DecisionRequest(**base)

async def test_finalize_when_all_good():
    r = await evaluate(req(), x_internal_token=settings.internal_token)
    assert r.action_code == "FINALIZE_BUILD" and r.compatibility_status == "compatible" and r.fallback_used

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
    r = await evaluate(req(budget=10000, parts=[{"price": 40000, "in_stock": True}]), x_internal_token=settings.internal_token)
    assert r.action_code == "WAIT_FOR_PRICE_DROP"

async def test_stock_unknown_waits():
    r = await evaluate(req(parts=[{"price": 40000, "in_stock": None}]), x_internal_token=settings.internal_token)
    assert r.action_code == "WAIT_FOR_PRICE_DROP"

async def test_unknown_price_waits_without_reporting_zero_total():
    r = await evaluate(req(parts=[{"price": None, "in_stock": None}], degraded_services=["price"]),
                       x_internal_token=settings.internal_token)
    assert r.action_code == "WAIT_FOR_PRICE_DROP"
    assert any("Total price is unavailable" in reason for reason in r.reasons)
    assert all("Total 0 THB" not in reason for reason in r.reasons)

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
    exp, used, fb = validate_and_lock("AVOID_COMBINATION", {"action_code": "FINALIZE_BUILD", "summary": "x", "reasons": [], "immediate_actions": []}, [], None)
    assert used is False and fb is True

async def test_unsupported_locale_rejected():
    with pytest.raises(Exception):
        await evaluate(req(locale="fr-FR"), x_internal_token=settings.internal_token)
