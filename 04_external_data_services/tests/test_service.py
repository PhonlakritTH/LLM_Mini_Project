import pytest
from app.config import settings
from app import breaker, cache as cache_mod
from app.main import query
from app.models import QueryRequest

@pytest.fixture(autouse=True)
def reset():
    breaker.reset(); cache_mod.cache.clear(); settings.mock_fail = ""

async def test_happy_path():
    r = await query(QueryRequest(part_ids=["Ryzen 5 7600", "RTX 4060"]), x_internal_token=settings.internal_token)
    assert len(r.prices) == 2 and r.data_quality.coverage == 1.0 and not r.degraded
    assert r.prices[0].source == "price_primary"

async def test_requires_token():
    with pytest.raises(Exception):
        await query(QueryRequest(part_ids=["Ryzen 5 7600"]), x_internal_token="bad")

async def test_failover_to_backup_provider():
    settings.mock_fail = "price_primary"
    r = await query(QueryRequest(part_ids=["Ryzen 5 7600"]), x_internal_token=settings.internal_token)
    assert r.prices and r.prices[0].source == "price_backup" and r.degraded

async def test_all_price_providers_down_returns_empty_and_degraded():
    settings.mock_fail = "price_primary,price_backup"
    r = await query(QueryRequest(part_ids=["Ryzen 5 7600"]), x_internal_token=settings.internal_token)
    assert r.prices == [] and r.degraded

async def test_manufacturer_spec_has_authority_field():
    r = await query(QueryRequest(part_ids=["Ryzen 5 7600"], fields=["spec"]), x_internal_token=settings.internal_token)
    assert r.specs[0].authority == "manufacturer" and r.specs[0].socket == "AM5"

async def test_cache_hit_returns_same_object():
    settings.mock_fail = ""
    a = await query(QueryRequest(part_ids=["RTX 4060"], fields=["price"]), x_internal_token=settings.internal_token)
    b = await query(QueryRequest(part_ids=["RTX 4060"], fields=["price"]), x_internal_token=settings.internal_token)
    assert a is b
