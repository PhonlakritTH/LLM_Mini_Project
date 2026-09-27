"""Builds the final, user-facing response. Order: action -> reason -> alternatives -> sources.
Never hides an out-of-stock or discontinued alert."""
from datetime import datetime, timedelta, timezone
from .config import settings
from .models import FormatRequest, RecommendationResponse, now_iso
from .warranty import contacts_for

SUMMARY_PREFIX = {"FINALIZE_BUILD": "", "SWAP_COMPONENT": "", "WAIT_FOR_PRICE_DROP": "", "AVOID_COMBINATION": "⚠ "}

def build_response(req: FormatRequest) -> RecommendationResponse:
    limitations = []
    if req.degraded_services:
        limitations.append(f"Some data could not be verified: {', '.join(req.degraded_services)}.")
    if req.escalate:
        limitations.append("This build was flagged for extra review; treat the result as lower-confidence.")
    out_of_stock = [p.name for p in req.parts if p.in_stock is False]
    if out_of_stock:
        limitations.append(f"Out of stock right now: {', '.join(out_of_stock)}.")  # never hidden

    immediate = list(req.immediate_actions)
    setup = ["Confirm final price and stock at checkout before paying.",
             "Verify PSU wattage and cable connectors match the GPU before installation."]
    if req.compatibility_status == "incompatible":
        setup.insert(0, "Do not purchase the current combination; resolve the conflict first.")

    fetched = now_iso()
    expires = (datetime.now(timezone.utc) + timedelta(seconds=settings.price_alert_refresh_interval)).isoformat()
    live = settings.feature_flag_live_alerts and req.consent_live_updates

    return RecommendationResponse(
        schema_version=settings.recommendation_schema_version, request_id=req.request_id, conversation_id=req.conversation_id,
        action_code=req.action_code, compatibility_status=req.compatibility_status, confidence=req.confidence,
        short_summary=SUMMARY_PREFIX[req.action_code] + req.summary, immediate_actions=immediate,
        primary_build=req.parts, alternatives=req.alternatives, setup_instructions=setup,
        manufacturer_support_contacts=[c for c in contacts_for(req.locale, settings.warranty_contact_directory_version)],
        reasons=req.reasons, sources=req.citations, observed_at=req.price_observed_at, fetched_at=fetched, expires_at=expires,
        limitations=limitations, degraded_services=req.degraded_services, live_updates_enabled=live, versions=req.versions)
