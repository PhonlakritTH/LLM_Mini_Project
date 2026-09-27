from app.config import settings
from app.main import build, feedback, safety_queue
from app.models import FormatRequest, Feedback
from app import feedback as fb_store, alerts

def req(**k):
    base = dict(request_id="r1", conversation_id="c1", action_code="FINALIZE_BUILD", compatibility_status="compatible",
               confidence=0.9, escalate=False, summary="All good.", reasons=["ok"], immediate_actions=[],
               citations=[], parts=[{"type": "gpu", "name": "RTX 4060", "price": 10500, "in_stock": True}], versions={"policy": "p1"})
    base.update(k); return FormatRequest(**base)

def test_order_and_fields():
    r = build(req(), x_internal_token=settings.internal_token)
    assert r.action_code == "FINALIZE_BUILD" and r.short_summary and r.primary_build and r.manufacturer_support_contacts

def test_avoid_prepends_warning_and_setup_step():
    r = build(req(action_code="AVOID_COMBINATION", compatibility_status="incompatible", summary="Conflict found."),
             x_internal_token=settings.internal_token)
    assert r.short_summary.startswith("⚠") and "Do not purchase" in r.setup_instructions[0]

def test_out_of_stock_never_hidden():
    r = build(req(parts=[{"type": "gpu", "name": "RTX 4060", "price": 10500, "in_stock": False}]), x_internal_token=settings.internal_token)
    assert any("Out of stock" in l for l in r.limitations)

def test_degraded_services_surface_as_limitation():
    r = build(req(degraded_services=["stock"]), x_internal_token=settings.internal_token)
    assert any("stock" in l for l in r.limitations)

def test_th_locale_gets_thai_warranty_region():
    r = build(req(locale="th-TH"), x_internal_token=settings.internal_token)
    assert all(c.region == "TH" for c in r.manufacturer_support_contacts)

def test_feedback_is_pseudonymous():
    r = feedback(Feedback(request_id="r1", user_id="user-42", category="helpful"), x_internal_token=settings.internal_token)
    assert r.pseudonymous_id != "user-42" and not r.routed_to_safety_review

def test_unsafe_feedback_routes_to_safety_queue():
    fb_store.SAFETY_QUEUE.clear()
    feedback(Feedback(request_id="r1", user_id="user-42", category="unsafe", comment="wrong wattage calc"), x_internal_token=settings.internal_token)
    q = safety_queue(x_internal_token=settings.internal_token)
    assert len(q) == 1 and q[0]["category"] == "unsafe"

def test_alert_cooldown_dedupes():
    alerts.reset()
    assert alerts.should_send("u1", "RTX 4060", consent=True)
    assert not alerts.should_send("u1", "RTX 4060", consent=True)

def test_alert_requires_consent():
    alerts.reset()
    assert not alerts.should_send("u1", "RTX 4060", consent=False)

def test_reviewed_only_feedback_eligible_for_training():
    fb_store.STORE.clear()
    feedback(Feedback(request_id="r9", user_id="u9", category="incorrect"), x_internal_token=settings.internal_token)
    assert fb_store.reviewed_for_training() == []
