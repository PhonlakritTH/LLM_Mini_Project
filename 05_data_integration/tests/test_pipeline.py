from datetime import datetime, timedelta, timezone
from app.config import settings
from app.main import snapshot
from app.models import IntegrationRequest, RawRecord

def rec(**k):
    observed_at = datetime.now(timezone.utc).isoformat()
    k.setdefault("observed_at", observed_at)
    return RawRecord(fetched_at=observed_at,
                     expires_at=(datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat(), **k)

def test_happy_path():
    req = IntegrationRequest(request_id="r1", budget=50000, use_case="gaming", records=[
        rec(kind="price", part_id="Ryzen 5 7600", source="price_primary", fields={"price": 7500}),
        rec(kind="stock", part_id="Ryzen 5 7600", source="stock_primary", fields={"in_stock": True}),
        rec(kind="spec", part_id="Ryzen 5 7600", source="spec_primary", authority="manufacturer", fields={"socket": "AM5"}),
    ])
    snap = snapshot(req, x_internal_token=settings.internal_token)
    p = snap.parts[0]
    assert p.price == 7500 and p.in_stock and p.socket == "AM5" and not p.degraded
    assert snap.data_quality.coverage == 1.0

def test_missing_price_flagged_and_degraded():
    req = IntegrationRequest(request_id="r2", records=[
        rec(kind="stock", part_id="RTX 4060", source="stock_primary", fields={"in_stock": True})])
    snap = snapshot(req, x_internal_token=settings.internal_token)
    assert snap.parts[0].degraded and any(f.flag == "missing" for f in snap.data_quality.flags)

def test_requested_parts_remain_unknown_when_providers_return_no_records():
    req = IntegrationRequest(request_id="r7", records=[], requested_parts=[
        {"part_id": "Ryzen 5 7600", "category": "cpu", "socket": "AM5"},
        {"part_id": "Owned PSU", "category": "psu", "owned": True, "wattage_draw": 650},
    ])
    snap = snapshot(req, x_internal_token=settings.internal_token)
    parts = {part.part_id: part for part in snap.parts}
    assert parts["Ryzen 5 7600"].price is None and parts["Ryzen 5 7600"].in_stock is None
    assert parts["Ryzen 5 7600"].degraded
    assert parts["Owned PSU"].owned and parts["Owned PSU"].price == 0 and not parts["Owned PSU"].degraded
    assert snap.data_quality.coverage == 0.0

def test_manufacturer_spec_wins_over_retailer():
    req = IntegrationRequest(request_id="r3", records=[
        rec(kind="spec", part_id="X", source="retailer-a", authority="retailer", fields={"socket": "WRONG"}),
        rec(kind="spec", part_id="X", source="spec_primary", authority="manufacturer", fields={"socket": "AM5"}),
    ])
    snap = snapshot(req, x_internal_token=settings.internal_token)
    assert snap.parts[0].socket == "AM5"

def test_conflicting_prices_flagged():
    req = IntegrationRequest(request_id="r4", records=[
        rec(kind="price", part_id="Y", source="a", observed_at="2026-09-27T09:00:00+00:00", fields={"price": 10000}),
        rec(kind="price", part_id="Y", source="b", observed_at="2026-09-27T10:00:00+00:00", fields={"price": 15000}),
    ])
    snap = snapshot(req, x_internal_token=settings.internal_token)
    assert any(f.flag == "conflicting" for f in snap.data_quality.flags)

def test_invalid_record_quarantined():
    req = IntegrationRequest(request_id="r5", records=[rec(kind="price", part_id="", source="a", fields={"price": 1})])
    snap = snapshot(req, x_internal_token=settings.internal_token)
    assert len(snap.quarantined) == 1 and snap.parts == []

def test_stale_price_flagged():
    old = rec(kind="price", part_id="Z", source="a", fields={"price": 1000})
    old.observed_at = "2020-01-01T00:00:00+00:00"
    req = IntegrationRequest(request_id="r6", records=[old])
    snap = snapshot(req, x_internal_token=settings.internal_token)
    assert any(f.flag == "stale" for f in snap.data_quality.flags) and not snap.data_quality.freshness_ok
