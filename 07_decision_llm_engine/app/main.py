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
    total = sum(p.get("price") or 0 for p in req.parts)
    stock_unknown = any(p.get("in_stock") is None for p in req.parts)
    good_alt = bool(req.alternatives.get("options")) and any(o.get("price_delta", 1) <= 0 or o.get("value_score", 0) > 0 for o in req.alternatives.get("options", []))
    price_high = "price" in req.degraded_services

    action, compat_bucket, fired = decide(req.budget, total, compat.get("status", "NEEDS_REVIEW"),
                                          compat.get("hard_override", False), stock_unknown, good_alt, price_high)
    trace += fired
    missing_evidence = bool(req.degraded_services) or not req.data_quality.get("freshness_ok", True)
    conflicting = any(f.get("flag") == "conflicting" for f in req.data_quality.get("flags", []))
    conf, escalate = confidence_and_escalation(compat.get("score", 0.9), compat.get("uncertainty", 0.1), missing_evidence, conflicting)
    trace.append(f"confidence={conf} escalate={escalate}")

    reasons_in = [f"reason_code:{r}" for r in compat.get("reason_codes", [])] + [f"Total {total:,} THB vs budget {req.budget:,} THB."]
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
