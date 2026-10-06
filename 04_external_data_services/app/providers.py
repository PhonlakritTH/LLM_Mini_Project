"""Live provider connectors convert provider responses into canonical records."""
import asyncio, re, time
from statistics import median
from typing import Callable
import httpx
from .config import settings

class ProviderError(Exception):
    def __init__(self, provider, status=None, retryable=False, retry_after=None):
        super().__init__(f"{provider} failed (status={status})")
        self.provider, self.status, self.retryable, self.retry_after = provider, status, retryable, retry_after

RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}

class PricePrimary:
    name = "price_primary"

    async def call(self, part_ids: list[str], search_terms: dict[str, list[str]] | None = None) -> dict:
        if not settings.serpapi_api_key:
            raise ProviderError(self.name, status=503)

        started = time.monotonic()
        semaphore = asyncio.Semaphore(3)
        async with httpx.AsyncClient(timeout=settings.provider_timeout) as client:
            async def lookup(part_id: str):
                async with semaphore:
                    query = part_id
                    if ("intel" in part_id.lower() or "ryzen" in part_id.lower()) and not part_id.lower().startswith("cpu"):
                        query = f"CPU {part_id}"
                    elif "kingston" in part_id.lower() and not part_id.lower().startswith("ram"):
                        query = f"RAM {part_id}"
                    response = await client.get("https://serpapi.com/search.json", params={
                        "engine": "google_shopping",
                        "q": query,
                        "google_domain": settings.google_domain,
                        "gl": settings.google_country,
                        "hl": settings.google_language,
                        "location": settings.google_location,
                        "api_key": settings.serpapi_api_key,
                    })
                    if response.status_code >= 400:
                        status = response.status_code
                        raise ProviderError(self.name, status=status, retryable=status in RETRYABLE_STATUS)
                    return part_id, response.json()

            try:
                results = await asyncio.gather(*(lookup(part_id) for part_id in part_ids))
            except httpx.TransportError as error:
                raise ProviderError(self.name, status=503, retryable=True) from error

        data = {}
        prebuilt_kw = ("desktop", "laptop", "notebook", "all-in-one", "aio", "คอมประกอบ", "ชุดคอม", "คอมพิวเตอร์", "ครบชุด")
        for part_id, payload in results:
            terms = (search_terms or {}).get(part_id, [])
            required = {term.lower() for term in terms if term.lower() not in ("cpu", "ram")}
            if not required:
                required = set(re.findall(r"[a-z0-9]+", part_id.lower())) - {"cpu", "ram"}
            is_case = any(w in part_id.lower() for w in ("case", "forge", "chassis"))
            is_cpu = "intel" in part_id.lower() or "ryzen" in part_id.lower()
            candidates = []
            for item in payload.get("shopping_results", []):
                title_lower = item.get("title", "").lower()
                if not is_case and any(kw in title_lower for kw in prebuilt_kw):
                    continue
                if is_cpu and any(kw in title_lower for kw in ("mainboard", "motherboard", "เมนบอร์ด")):
                    continue
                title_tokens = set(re.findall(r"[a-z0-9]+", title_lower))
                price_text = str(item.get("price", ""))
                price = item.get("extracted_price")
                if (required and required.issubset(title_tokens) and isinstance(price, (int, float))
                        and price > 0 and ("฿" in price_text or "thb" in price_text.lower())):
                    candidates.append((round(price), item))
            if candidates:
                prices = sorted(price for price, _ in candidates)
                m = median(prices)
                filtered = [p for p in prices if 0.5 * m <= p <= 1.8 * m]
                if not filtered:
                    filtered = prices
                data[part_id] = {
                    "price": round(median(filtered)),
                    "low_price": filtered[0],
                    "high_price": filtered[-1],
                    "observation_count": len(filtered),
                }

        return {"data": data, "latency_ms": round((time.monotonic() - started) * 1000, 1)}

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
