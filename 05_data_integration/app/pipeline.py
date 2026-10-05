"""Combine many sources into one repeatable, versioned, traceable snapshot."""
import hashlib, uuid
from datetime import datetime, timezone
from .config import settings
from .models import RawRecord, PartRecord, QualityFlag, DataQualitySummary, PartCatalogSnapshot

CATEGORY = {"cpu": "cpu", "gpu": "gpu", "motherboard": "motherboard", "psu": "psu", "ram": "ram", "storage": "storage", "case": "case"}
TIER_BY_PERF = [(85, "enthusiast"), (65, "mainstream"), (0, "entry")]

def _content_hash(rec: RawRecord) -> str:
    return hashlib.sha256(f"{rec.kind}|{rec.part_id}|{rec.source}|{rec.observed_at}".encode()).hexdigest()[:16]

def _is_stale(rec: RawRecord, now: datetime) -> bool:
    limit = {"price": settings.price_freshness_seconds, "stock": settings.stock_freshness_seconds,
             "benchmark": settings.benchmark_freshness_seconds, "spec": settings.benchmark_freshness_seconds}[rec.kind]
    age = (now - datetime.fromisoformat(rec.observed_at)).total_seconds()
    return age > limit

def _tier(perf: float | None) -> str | None:
    if perf is None: return None
    for cutoff, tier in TIER_BY_PERF:
        if perf >= cutoff: return tier
    return "entry"

def build_snapshot(req) -> PartCatalogSnapshot:
    now = datetime.now(timezone.utc)
    valid, quarantine, seen_hashes = [], [], set()
    for rec in req.records:
        # 1. schema check -> quarantine invalid
        if not rec.part_id or rec.kind not in ("price", "stock", "benchmark", "spec"):
            quarantine.append({"record": rec.model_dump(), "reason": "invalid_schema"}); continue
        h = _content_hash(rec)
        if h in seen_hashes:  # idempotent upsert: drop exact duplicates
            continue
        seen_hashes.add(h)
        valid.append(rec)

    by_part: dict[str, dict] = {}
    for part in req.requested_parts:
        part_id = part["part_id"]
        by_part[part_id] = {key: part.get(key) for key in
                    ("category", "socket", "chipset", "form_factor", "wattage_draw")}
        by_part[part_id]["owned"] = bool(part.get("owned", False))
        by_part[part_id]["lineage"] = {}
        if part.get("owned"):
            by_part[part_id].update(price=0, in_stock=True, owned=True)

    flags: list[QualityFlag] = []
    for rec in valid:
        p = by_part.setdefault(rec.part_id, {"lineage": {}})
        stale = _is_stale(rec, now)
        if rec.kind == "price":
            existing = p.get("price")
            # conflict resolution: manufacturer authority beats retailer; else most recent wins
            if existing is None or rec.authority == "manufacturer" or rec.observed_at > p.get("price_observed_at", ""):
                if existing is not None and abs(existing - rec.fields["price"]) / max(existing, 1) > 0.15:
                    flags.append(QualityFlag(part_id=rec.part_id, flag="conflicting",
                                             detail=f"Price sources disagree: {existing} vs {rec.fields['price']}."))
                p["price"] = rec.fields["price"]; p["price_observed_at"] = rec.observed_at
            p.setdefault("lineage", {}).setdefault("price", []).append(rec.source)
            if stale: flags.append(QualityFlag(part_id=rec.part_id, flag="stale", detail="Price observation is older than the freshness limit."))
        elif rec.kind == "stock":
            p["in_stock"] = rec.fields["in_stock"]; p["lineage"].setdefault("stock", []).append(rec.source)
            if not rec.fields["in_stock"]: flags.append(QualityFlag(part_id=rec.part_id, flag="out_of_stock", detail="Marked out of stock by provider."))
        elif rec.kind == "benchmark":
            p["performance_index"] = rec.fields.get("performance_index"); p["lineage"].setdefault("benchmark", []).append(rec.source)
        elif rec.kind == "spec":
            for f in ("socket", "chipset", "form_factor", "wattage_draw"):
                if rec.fields.get(f) is not None:
                    if rec.authority == "manufacturer" or f not in p:
                        p[f] = rec.fields[f]
            p["lineage"].setdefault("spec", []).append(rec.source)
        p["category"] = p.get("category") or CATEGORY.get(rec.part_id.split()[0].lower(), "part")

    parts: list[PartRecord] = []
    requested_ids = set(by_part) | {r.part_id for r in valid}
    for pid in requested_ids:
        d = by_part.get(pid, {})
        owned = d.get("owned", False)
        missing_price = not owned and "price" not in d.get("lineage", {})
        if missing_price: flags.append(QualityFlag(part_id=pid, flag="missing", detail="No price record available."))
        socket, form_factor, watts = d.get("socket"), d.get("form_factor"), d.get("wattage_draw")
        group = "|".join(filter(None, [socket, form_factor])) or None
        degraded = not owned and (missing_price or d.get("in_stock") is None or
                    any(f.part_id == pid and f.flag in ("stale", "conflicting") for f in flags))
        parts.append(PartRecord(part_id=pid, category=d.get("category", "part"), price=d.get("price"), price_thb=d.get("price"),
                                in_stock=d.get("in_stock"), performance_index=d.get("performance_index"),
                                socket=socket, chipset=d.get("chipset"), form_factor=form_factor, wattage_draw=watts,
                                performance_tier=_tier(d.get("performance_index")), compatibility_group=group,
                                owned=owned, degraded=degraded, lineage=d.get("lineage", {})))

    purchasable = [part for part in parts if not part.owned]
    coverage = sum(1 for part in purchasable if part.price is not None) / len(purchasable) if purchasable else 1.0
    completeness = sum(1 for p in parts if p.socket or p.category not in ("cpu", "motherboard")) / len(parts) if parts else 1.0
    freshness_ok = not any(f.flag == "stale" for f in flags)
    score = round(settings.quality_weight_freshness * (1.0 if freshness_ok else 0.0) +
                 settings.quality_weight_coverage * coverage + settings.quality_weight_completeness * completeness, 3)
    dq = DataQualitySummary(coverage=round(coverage, 3), freshness_ok=freshness_ok, completeness=round(completeness, 3),
                            quality_score=score, flags=flags)
    return PartCatalogSnapshot(snapshot_id=uuid.uuid4().hex, schema_version=settings.canonical_schema_version,
                               currency=settings.default_currency, request_id=req.request_id, budget=req.budget,
                               use_case=req.use_case, parts=parts, quarantined=quarantine, data_quality=dq,
                               created_at=now.isoformat())
