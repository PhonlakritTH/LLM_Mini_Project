"""Explainable baseline + hard rule overrides. Recall on INCOMPATIBLE matters more than precision:
a false 'compatible' can break a build, so ties lean toward NEEDS_REVIEW rather than COMPATIBLE."""
from .config import settings
from .models import CompatibilityAssessment

def _features(parts: list[dict], constraints: dict) -> dict:
    by = {p["type"] if "type" in p else p.get("category"): p for p in parts}
    cpu, mb, gpu, psu = by.get("cpu"), by.get("motherboard"), by.get("gpu"), by.get("psu")
    watts = (cpu.get("wattage_draw") or 65 if cpu else 0) + (gpu.get("wattage_draw") or gpu.get("watts") or 0 if gpu else 0) + 100
    return {"cpu": cpu, "mb": mb, "gpu": gpu, "psu": psu, "need_watts": watts,
            "max_watts": constraints.get("max_wattage"), "case_ff": constraints.get("case_form_factor")}

def assess(parts: list[dict], constraints: dict) -> CompatibilityAssessment:
    f = _features(parts, constraints)
    reasons, hard = [], False
    cpu_sock = (f["cpu"] or {}).get("socket")
    mb_sock = (f["mb"] or {}).get("socket") or (f["mb"] or {}).get("compatibility_group", "").split("|")[0] or None
    score, uncertainty = 0.95, 0.05

    if f["cpu"] and f["mb"]:
        if not cpu_sock or not mb_sock:
            score, uncertainty = 0.5, 0.35
            reasons.append("unknown_socket_data")
        elif cpu_sock != mb_sock:
            score, uncertainty, hard = 0.02, 0.05, True
            reasons.append(f"socket_mismatch:{cpu_sock}!={mb_sock}")
    psu_watts = (f["psu"] or {}).get("wattage") or (f["psu"] or {}).get("wattage_draw")
    if psu_watts:
        headroom = psu_watts - f["need_watts"]
        if headroom < 0:
            score, uncertainty, hard = min(score, 0.03), 0.05, True
            reasons.append(f"psu_insufficient:{psu_watts}W<{f['need_watts']}W")
        elif headroom < f["need_watts"] * 0.2:
            score = min(score, 0.55)
            reasons.append(f"psu_low_headroom:{psu_watts}W~{f['need_watts']}W")
    if f["max_watts"] and f["need_watts"] > f["max_watts"]:
        score = min(score, 0.5)
        reasons.append(f"exceeds_wattage_limit:{f['need_watts']}W>{f['max_watts']}W")
    if f["case_ff"] == "ITX" and f["mb"] and (f["mb"].get("form_factor") or "mATX") != "ITX":
        score, uncertainty, hard = 0.02, 0.05, True
        reasons.append("case_form_factor_conflict")

    thresholds = (settings.value_threshold_compatible, settings.value_threshold_needs_review)
    status = "INCOMPATIBLE" if hard else ("COMPATIBLE" if score >= thresholds[0] else
             "NEEDS_REVIEW" if score >= thresholds[1] else "INCOMPATIBLE")
    if not reasons: reasons.append("all_checks_passed")
    return CompatibilityAssessment(status=status, score=round(score, 3), uncertainty=uncertainty, reason_codes=reasons,
                                   hard_override=hard, model_version=settings.model_version,
                                   feature_schema_version=settings.feature_schema_version)
