import json
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Header, HTTPException
from .config import settings
from .models import QueryRequest, QueryResponse, PriceListing, ProviderHealth, DataQuality, now_iso
from .providers import PricePrimary, ProviderError, with_retry
from .cache import cache
from . import breaker

app = FastAPI(title="External Data Services", version="1.0")

async def _price(part_ids: list[str], search_terms: dict[str, list[str]]) -> tuple[list[PriceListing], ProviderHealth]:
    name = PricePrimary.name
    if breaker.is_open(name):
        return [], ProviderHealth(provider=name, healthy=False, latency_ms=0, breaker_open=True)
    try:
        r = await with_retry(lambda: PricePrimary().call(part_ids, search_terms), name)
        breaker.record(name, True)
        fetched = now_iso()
        listings = [PriceListing(part_id=pid, price=v["price"],
                                 low_price=v["low_price"], high_price=v["high_price"],
                                 observation_count=v["observation_count"],
                                 source="Google Shopping via SerpApi", fetched_at=fetched, observed_at=fetched,
                                 expires_at=(datetime.now(timezone.utc) + timedelta(seconds=settings.cache_ttl_price)).isoformat())
                    for pid, v in r["data"].items()]
        return listings, ProviderHealth(provider=name, healthy=True, latency_ms=r["latency_ms"], breaker_open=False)
    except ProviderError as e:
        breaker.record(name, False)
        health = ProviderHealth(provider=name, healthy=False, latency_ms=0, breaker_open=breaker.is_open(name), last_error=str(e))
        return [], health

@app.post("/v1/external/query", response_model=QueryResponse)
async def query(req: QueryRequest, x_internal_token: str = Header(default="")):
    if x_internal_token != settings.internal_token:
        raise HTTPException(401, "UNAUTHORIZED")
    ck = cache.key("query", ",".join(sorted(req.part_ids)), ",".join(sorted(req.fields)),
                   json.dumps(req.search_terms, sort_keys=True), req.locale, "v2", "THB")
    cached = cache.get(ck)
    if cached: return cached

    prices, health = [], []
    if "price" in req.fields:
        prices, h = await _price(req.part_ids, req.search_terms); health.append(h)

    got_prices = {p.part_id for p in prices}
    coverage = len(got_prices) / len(req.part_ids) if req.part_ids else 1.0
    degraded = any(not h.healthy for h in health) or coverage < 1
    dq = DataQuality(coverage=coverage, freshness_ok=not degraded, disagreement=[])
    resp = QueryResponse(prices=prices, provider_health=health,
                         data_quality=dq, degraded=degraded)
    cache.set(ck, resp, settings.cache_ttl_price)  # shortest TTL among included fields
    return resp

@app.get("/health")
def health(): return {"status": "ok"}
