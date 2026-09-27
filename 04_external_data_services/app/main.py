import time
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Header, HTTPException
from .config import settings
from .models import (QueryRequest, QueryResponse, PriceListing, StockStatus, BenchmarkScore, SpecRecord,
                      ProviderHealth, DataQuality, now_iso)
from .providers import PricePrimary, PriceBackup, StockPrimary, BenchmarkPrimary, SpecPrimary, ProviderError, with_retry
from .cache import cache
from . import breaker
from .quality import performance_index, quality_score

app = FastAPI(title="External Data Services", version="1.0")

async def _price(part_ids: list[str]) -> tuple[list[PriceListing], ProviderHealth, bool]:
    for connector, name in ((PricePrimary("price_primary"), "price_primary"), (PriceBackup("price_backup"), "price_backup")):
        if breaker.is_open(name): continue
        try:
            r = await with_retry(lambda: connector.call(part_ids), name)
            breaker.record(name, True)
            fetched = now_iso()
            listings = [PriceListing(part_id=pid, retailer=v["retailer"], price=v["price"], discount_pct=v["discount_pct"],
                                     source=name, fetched_at=fetched, observed_at=fetched,
                                     expires_at=(datetime.now(timezone.utc) + timedelta(seconds=settings.cache_ttl_price)).isoformat())
                        for pid, v in r["data"].items()]
            return listings, ProviderHealth(provider=name, healthy=True, latency_ms=r["latency_ms"], breaker_open=False), name == "price_backup"
        except ProviderError as e:
            breaker.record(name, False)
            last = ProviderHealth(provider=name, healthy=False, latency_ms=0, breaker_open=breaker.is_open(name), last_error=str(e))
    return [], last, True  # both failed -> caller may fall back to stale cache

async def _stock(part_ids):
    name = "stock_primary"
    try:
        r = await with_retry(lambda: StockPrimary(name).call(part_ids), name)
        breaker.record(name, True)
        fetched = now_iso()
        out = [StockStatus(part_id=pid, retailer=v["retailer"], in_stock=v["in_stock"], warehouse=v.get("warehouse"),
                           source=name, fetched_at=fetched, observed_at=fetched,
                           expires_at=(datetime.now(timezone.utc) + timedelta(seconds=settings.cache_ttl_stock)).isoformat())
               for pid, v in r["data"].items()]
        return out, ProviderHealth(provider=name, healthy=True, latency_ms=r["latency_ms"], breaker_open=False)
    except ProviderError as e:
        breaker.record(name, False)
        return [], ProviderHealth(provider=name, healthy=False, latency_ms=0, breaker_open=breaker.is_open(name), last_error=str(e))

async def _benchmark(part_ids):
    name = "benchmark_primary"
    try:
        r = await with_retry(lambda: BenchmarkPrimary(name).call(part_ids), name)
        breaker.record(name, True)
        fetched = now_iso()
        out = [BenchmarkScore(part_id=pid, passmark=v.get("passmark"), game_fps_1080p=v.get("game_fps_1080p"),
                              performance_index=performance_index(passmark=v.get("passmark"), fps=v.get("game_fps_1080p")),
                              source=name, fetched_at=fetched, observed_at=fetched,
                              expires_at=(datetime.now(timezone.utc) + timedelta(seconds=settings.cache_ttl_benchmark)).isoformat())
               for pid, v in r["data"].items()]
        return out, ProviderHealth(provider=name, healthy=True, latency_ms=r["latency_ms"], breaker_open=False)
    except ProviderError as e:
        breaker.record(name, False)
        return [], ProviderHealth(provider=name, healthy=False, latency_ms=0, breaker_open=breaker.is_open(name), last_error=str(e))

async def _spec(part_ids):
    name = "spec_primary"
    r = await with_retry(lambda: SpecPrimary(name).call(part_ids), name)
    fetched = now_iso()
    out = [SpecRecord(part_id=pid, socket=v.get("socket"), wattage_draw=v.get("wattage_draw"), authority="manufacturer",
                      source=name, fetched_at=fetched, observed_at=fetched,
                      expires_at=(datetime.now(timezone.utc) + timedelta(days=30)).isoformat())
           for pid, v in r["data"].items()]
    return out, ProviderHealth(provider=name, healthy=True, latency_ms=r["latency_ms"], breaker_open=False)

@app.post("/v1/external/query", response_model=QueryResponse)
async def query(req: QueryRequest, x_internal_token: str = Header(default="")):
    if x_internal_token != settings.internal_token:
        raise HTTPException(401, "UNAUTHORIZED")
    ck = cache.key("query", ",".join(sorted(req.part_ids)), ",".join(sorted(req.fields)), "v1", "THB")
    cached = cache.get(ck)
    if cached: return cached

    prices, stock, benches, specs, health = [], [], [], [], []
    used_backup = False
    if "price" in req.fields:
        prices, h, used_backup = await _price(req.part_ids); health.append(h)
    if "stock" in req.fields:
        s, h = await _stock(req.part_ids); stock = s; health.append(h)
    if "benchmark" in req.fields:
        b, h = await _benchmark(req.part_ids); benches = b; health.append(h)
    if "spec" in req.fields:
        sp, h = await _spec(req.part_ids); specs = sp; health.append(h)

    got_prices = {p.part_id for p in prices}
    coverage = len(got_prices) / len(req.part_ids) if req.part_ids else 1.0
    degraded = any(not h.healthy for h in health) or used_backup
    dq = DataQuality(coverage=coverage, freshness_ok=not degraded, disagreement=[])
    resp = QueryResponse(prices=prices, stock=stock, benchmarks=benches, specs=specs, provider_health=health,
                         data_quality=dq, degraded=degraded)
    cache.set(ck, resp, settings.cache_ttl_price)  # shortest TTL among included fields
    return resp

@app.get("/health")
def health(): return {"status": "ok"}
