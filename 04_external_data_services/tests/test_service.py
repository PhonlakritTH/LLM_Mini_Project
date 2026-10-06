import pytest
import httpx
from pydantic import ValidationError
from app.config import settings
from app import breaker, cache as cache_mod
from app.main import query
from app.models import QueryRequest


@pytest.fixture(autouse=True)
def reset():
    breaker.reset()
    cache_mod.cache.clear()
    settings.serpapi_api_key = "test-key"


async def test_live_price_results_become_a_matched_reference_range(monkeypatch):
    class Response:
        status_code = 200

        def json(self):
            return {"shopping_results": [
                {"title": "AMD Ryzen 5 7600 Processor", "extracted_price": 7590, "price": "7,590 ฿"},
                {"title": "AMD Ryzen 5 7600 CPU", "extracted_price": 7790, "price": "7,790 THB"},
                {"title": "AMD Ryzen 5 5600 Processor", "extracted_price": 5990, "price": "5,990 ฿"},
            ]}

        def raise_for_status(self):
            pass

    class Client:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            pass

        async def get(self, _url, params):
            assert params["engine"] == "google_shopping" and params["gl"] == "th"
            return Response()

    monkeypatch.setattr(httpx, "AsyncClient", Client)
    req = QueryRequest(part_ids=["Ryzen 5 7600"], fields=["price"],
                       search_terms={"Ryzen 5 7600": ["amd", "ryzen", "7600"]})
    response = await query(req, x_internal_token=settings.internal_token)
    assert response.data_quality.coverage == 1 and not response.degraded
    assert response.prices[0].price == 7690
    assert (response.prices[0].low_price, response.prices[0].high_price) == (7590, 7790)
    assert response.prices[0].observation_count == 2
    assert response.prices[0].source == "Google Shopping via SerpApi"


async def test_requires_internal_token():
    with pytest.raises(Exception):
        await query(QueryRequest(part_ids=["Ryzen 5 7600"]), x_internal_token="bad")


async def test_missing_provider_key_returns_no_fabricated_price():
    settings.serpapi_api_key = ""
    response = await query(QueryRequest(part_ids=["Ryzen 5 7600"]), x_internal_token=settings.internal_token)
    assert response.prices == [] and response.degraded


async def test_unmatched_model_is_not_given_a_price(monkeypatch):
    class Response:
        status_code = 200

        def json(self):
            return {"shopping_results": [
                {"title": "AMD Ryzen 5 5600 Processor", "extracted_price": 5990, "price": "5,990 ฿"}
            ]}

        def raise_for_status(self):
            pass

    class Client:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            pass

        async def get(self, *_args, **_kwargs):
            return Response()

    monkeypatch.setattr(httpx, "AsyncClient", Client)
    response = await query(QueryRequest(part_ids=["Ryzen 5 7600"], fields=["price"],
                           search_terms={"Ryzen 5 7600": ["amd", "ryzen", "7600"]}),
                           x_internal_token=settings.internal_token)
    assert response.prices == [] and response.data_quality.coverage == 0 and response.degraded


def test_stock_and_non_price_data_are_not_supported():
    with pytest.raises(ValidationError):
        QueryRequest(part_ids=["Ryzen 5 7600"], fields=["stock"])


async def test_cache_hit_returns_same_object():
    a = await query(QueryRequest(part_ids=["RTX 4060"], fields=[]), x_internal_token=settings.internal_token)
    b = await query(QueryRequest(part_ids=["RTX 4060"], fields=[]), x_internal_token=settings.internal_token)
    assert a is b
