import uuid
from fastapi import FastAPI, Header, HTTPException
from .config import settings
from .models import DecisionRequest, DecisionResult, Citation
from .rules import decide, confidence_and_escalation
from .explainer import build_prompt, call_llm, validate_and_lock

app = FastAPI(title="Decision and LLM Engine", version="1.0")

@app.post("/v1/decision/evaluate", response_model=DecisionResult)
async def evaluate(req: DecisionRequest, x_internal_token: str = Header(default="")):
    if x_internal_token != settings.internal_token:
        raise HTTPException(401, "UNAUTHORIZED")
    if req.locale not in settings.supported_locales.split(","):
        raise HTTPException(422, f"Unsupported locale: {req.locale}")

    trace = [f"request_id={req.request_id}"]
    compat = req.compatibility
    required_parts = [p for p in req.parts if not p.get("owned", False)]
    price_unknown = any(p.get("price") is None for p in required_parts)
    total = sum(p["price"] for p in required_parts) if not price_unknown else 0
    price_range = req.data_quality.get("total_price_range") or {}
    range_low, range_high = price_range.get("low"), price_range.get("high")
    range_over_budget = range_high is not None and range_high > req.budget
    range_overlaps_budget = (range_low is not None and range_high is not None and
                             range_low <= req.budget < range_high)
    good_alt = bool(req.alternatives.get("options")) and any(o.get("price_delta", 1) <= 0 or o.get("value_score", 0) > 0 for o in req.alternatives.get("options", []))
    price_uncertain = ("price" in req.degraded_services or price_unknown or range_overlaps_budget)
    decision_total = range_high if range_over_budget and not range_overlaps_budget else total
    if range_low is not None and range_high is not None:
        if range_over_budget and not range_overlaps_budget:
            decision_total = range_high
        elif total:
            decision_total = min(range_high, total)

    action, compat_bucket, fired = decide(req.budget, decision_total, compat.get("status", "NEEDS_REVIEW"),
                                          compat.get("hard_override", False), price_unknown, good_alt, price_uncertain)
    trace += fired
    missing_evidence = bool(req.degraded_services) or not req.data_quality.get("freshness_ok", True)
    conflicting = any(f.get("flag") == "conflicting" for f in req.data_quality.get("flags", []))
    conf, escalate = confidence_and_escalation(compat.get("score", 0.9), compat.get("uncertainty", 0.1), missing_evidence, conflicting)
    trace.append(f"confidence={conf} escalate={escalate}")

    reasons_in = [f"reason_code:{r}" for r in compat.get("reason_codes", [])]
    if price_unknown:
        reasons_in.append("Reference price data is incomplete; budget fit cannot be verified.")
    elif range_low is not None and range_high is not None:
        reasons_in.append(f"Reference range {range_low:,}-{range_high:,} THB vs budget {req.budget:,} THB.")
    else:
        reasons_in.append(f"Reference total {total:,} THB vs budget {req.budget:,} THB.")
    wattage_warning = next((f"⚠ {r}" for r in compat.get("reason_codes", []) if "psu" in r or "wattage" in r), None)

    evidence_package = {"compatibility": compat, "alternatives": req.alternatives.get("options", [])[:3],
                        "rag": req.evidence.get("passages", [])}
    raw = await call_llm(build_prompt(action, evidence_package))  # None in this mini project -> fixed template
    explanation, llm_used, fallback_used = validate_and_lock(action, raw, reasons_in, wattage_warning)
    trace.append(f"llm_used={llm_used} fallback_used={fallback_used}")

    citations = [Citation(document_id=p.get("document_id", "?"), section=p.get("section", "?")) for p in req.evidence.get("passages", [])[:3]]

    return DecisionResult(action_code=action, compatibility_status=compat_bucket, confidence=conf, escalate=escalate,
                          rules_fired=fired, summary=explanation["summary"], reasons=explanation["reasons"],
                          immediate_actions=explanation["immediate_actions"], citations=citations,
                          llm_used=llm_used, fallback_used=fallback_used, request_id=req.request_id,
                          conversation_id=req.conversation_id or req.request_id,
                          versions={"policy": settings.decision_policy_version, "prompt": settings.prompt_version,
                                    "model": settings.llm_model_explainer if llm_used else "fixed-template"},
                          audit_trace=trace)

@app.get("/health")
def health(): return {"status": "ok", "policy_version": settings.decision_policy_version}
