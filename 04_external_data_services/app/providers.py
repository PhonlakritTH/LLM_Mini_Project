"""Each connector shares the same interface & error contract; converts provider format -> canonical record.
Business logic never depends on a provider-specific response shape."""
import asyncio, random, time
from typing import Callable
from .config import settings
from .models import PriceListing, StockStatus, BenchmarkScore, SpecRecord, now_iso

class ProviderError(Exception):
    def __init__(self, provider, status=None, retryable=False, retry_after=None):
        super().__init__(f"{provider} failed (status={status})")
        self.provider, self.status, self.retryable, self.retry_after = provider, status, retryable, retry_after

RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}
CATALOG = {  # part_id -> canonical facts (stands in for retailer/manufacturer feeds)
    "Ryzen 5 7600": {"price": 7500, "socket": "AM5", "watts": 65}, "Core i5-13400F": {"price": 7900, "socket": "LGA1700", "watts": 65},
    "Ryzen 7 7700": {"price": 11500, "socket": "AM5", "watts": 65}, "Core i7-13700": {"price": 13500, "socket": "LGA1700", "watts": 65},
    "RTX 4060": {"price": 10500, "socket": None, "watts": 115}, "RX 7600": {"price": 8900, "socket": None, "watts": 165},
    "RTX 4060 Ti": {"price": 15500, "socket": None, "watts": 160}, "RTX 4070 Super": {"price": 25500, "socket": None, "watts": 220},
    "650W 80+ Bronze": {"price": 1900, "socket": None, "watts": None}, "1TB NVMe": {"price": 2200, "socket": None, "watts": None},
}

def _price_of(pid: str) -> int: return CATALOG.get(pid, {}).get("price", 5000)

class Connector:
    """Base: same call() signature for every provider. Subclasses only differ in data + failure name."""
    name: str
    def __init__(self, fail_flag: str, jitter=(0.0, 0.02)): self.fail_flag, self.jitter = fail_flag, jitter
    async def call(self, part_ids: list[str]) -> dict:
        t0 = time.monotonic()
        if self.fail_flag in settings.mock_fail.split(","):
            raise ProviderError(self.name, status=503, retryable=True, retry_after=0.05)
        await asyncio.sleep(random.uniform(*self.jitter))
        data = self._data(part_ids)
        return {"data": data, "latency_ms": round((time.monotonic() - t0) * 1000, 1)}
    def _data(self, part_ids): raise NotImplementedError

class PricePrimary(Connector):
    name = "price_primary"
    def _data(self, ids): return {i: {"price": _price_of(i), "retailer": "mock-retailer-a", "discount_pct": 0.0} for i in ids}

class PriceBackup(Connector):
    name = "price_backup"
    def _data(self, ids): return {i: {"price": int(_price_of(i) * 1.03), "retailer": "mock-retailer-b", "discount_pct": 0.0} for i in ids}

class StockPrimary(Connector):
    name = "stock_primary"
    def _data(self, ids): return {i: {"in_stock": True, "retailer": "mock-retailer-a", "warehouse": "BKK-1"} for i in ids}

class BenchmarkPrimary(Connector):
    name = "benchmark_primary"
    def _data(self, ids):
        return {i: {"passmark": 20000.0, "game_fps_1080p": 120.0, "performance_index": 80.0} for i in ids}

class SpecPrimary(Connector):
    name = "spec_primary"
    def _data(self, ids): return {i: {**{"socket": CATALOG.get(i, {}).get("socket"), "wattage_draw": CATALOG.get(i, {}).get("watts")}} for i in ids}

async def with_retry(fn: Callable, provider_name: str):
    """Retry only 408/429/temporary 5xx, honouring Retry-After; separate conn/read/total timeouts via provider_timeout."""
    delay_used = 0.0
    for attempt in range(3):
        try:
            return await asyncio.wait_for(fn(), timeout=settings.provider_timeout)
        except ProviderError as e:
            if not (e.retryable and (e.status in RETRYABLE_STATUS)) or attempt == 2:
                raise
            wait = e.retry_after or (0.05 * 2 ** attempt)
            delay_used += wait
            if delay_used > settings.provider_timeout: raise
            await asyncio.sleep(wait)
        except asyncio.TimeoutError:
            if attempt == 2: raise ProviderError(provider_name, status=408, retryable=True)
