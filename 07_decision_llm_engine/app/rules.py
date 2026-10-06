"""Versioned decision table. Hard compatibility rules always win (monotonic safety):
an incompatible/unsafe combination is never finalized by a downstream override."""
from .config import settings
from .models import ActionCode

def decide(budget: int, total_price: int, compat_status: str, hard_override: bool,
          data_incomplete: bool, has_good_alternative: bool, price_uncertain: bool) -> tuple[ActionCode, str, list[str]]:
    fired = [f"policy:{settings.decision_policy_version}"]
    if compat_status == "INCOMPATIBLE" or hard_override:
        fired.append("rule:hard_incompatible_blocks_finalize")
        if has_good_alternative:
            fired.append("rule:safe_alternative_available")
            return "SWAP_COMPONENT", "warning", fired
        fired.append("rule:no_safe_alternative")
        return "AVOID_COMBINATION", "incompatible", fired

    over_budget = total_price > budget * (1 + settings.budget_over_tolerance_pct / 100)
    if compat_status == "NEEDS_REVIEW":
        fired.append("rule:needs_review_treated_as_warning")

    if over_budget:
        fired.append("rule:over_budget")
        if has_good_alternative:
            fired.append("rule:cheaper_alternative_available")
            return "SWAP_COMPONENT", "warning", fired
        fired.append("rule:no_cheaper_alternative")
        return "RECONFIGURE_BUILD", "warning", fired

    if data_incomplete or price_uncertain:
        fired.append("rule:reference_price_or_evidence_uncertain")
        return "NEEDS_PRICE_DATA", "warning", fired

    if compat_status == "NEEDS_REVIEW":
        return "SWAP_COMPONENT" if has_good_alternative else "NEEDS_PRICE_DATA", "warning", fired

    fired.append("rule:all_checks_passed")
    return "FINALIZE_BUILD", "compatible", fired

def confidence_and_escalation(model_score: float, uncertainty: float, missing_evidence: bool, conflicting_prices: bool) -> tuple[float, bool]:
    conf = round(max(0.0, min(1.0, model_score - uncertainty - (0.15 if missing_evidence else 0) - (0.15 if conflicting_prices else 0))), 3)
    escalate = conf < 0.5 or missing_evidence or conflicting_prices
    return conf, escalate
