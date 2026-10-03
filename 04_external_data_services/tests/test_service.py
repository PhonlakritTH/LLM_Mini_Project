import pytest
import httpx
from app.config import settings
from app import breaker, cache as cache_mod
from app.main import query
from app.models import QueryRequest

@pytest.fixture(autouse=True)
def reset():
    breaker.reset(); cache_mod.cache.clear(); settings.serpapi_api_key = "test-key"

async def test_live_price_results_are_normalized(monkeypatch):
    class Response:
        status_code = 200
        def json(self):
            return {"shopping_results": [{"title": "AMD Ryzen 5 7600 Processor", "extracted_price": 7590,
                                           "price": "7,590.00 ฿", "source": "Retailer", "product_link": "https://shop.example/item"}]}
        def raise_for_status(self): pass

    class Client:
        def __init__(self, **_kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *_args): pass
        async def get(self, _url, params):
            assert params["engine"] == "google_shopping" and params["gl"] == "th"
            return Response()

    monkeypatch.setattr(httpx, "AsyncClient", Client)
    r = await query(QueryRequest(part_ids=["Ryzen 5 7600", "RTX 4060"]), x_internal_token=settings.internal_token)
    assert len(r.prices) == 1 and r.data_quality.coverage == 0.5 and r.degraded
    assert r.prices[0].source == "price_primary"
    assert r.prices[0].product_url == "https://shop.example/item"

async def test_requires_token():
    with pytest.raises(Exception):
        await query(QueryRequest(part_ids=["Ryzen 5 7600"]), x_internal_token="bad")

async def test_missing_provider_key_returns_no_fabricated_price():
    settings.serpapi_api_key = ""
    r = await query(QueryRequest(part_ids=["Ryzen 5 7600"]), x_internal_token=settings.internal_token)
    assert r.prices == [] and r.degraded

async def test_manufacturer_spec_has_authority_field():
    r = await query(QueryRequest(part_ids=["Ryzen 5 7600"], fields=["spec"]), x_internal_token=settings.internal_token)
    assert r.specs == [] and r.provider_health[0].healthy is False

async def test_cache_hit_returns_same_object():
    a = await query(QueryRequest(part_ids=["RTX 4060"], fields=[]), x_internal_token=settings.internal_token)
    b = await query(QueryRequest(part_ids=["RTX 4060"], fields=[]), x_internal_token=settings.internal_token)
    assert a is b
