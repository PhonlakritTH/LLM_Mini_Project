"""Allowlisted tools: fixed JSON contract, timeout, permission, retry, circuit breaker."""
import asyncio, random, time
from dataclasses import dataclass
from typing import Optional
import httpx
from pydantic import BaseModel
from .config import settings
from .state import AgentState, BudgetExceeded

class ToolDenied(Exception): ...
class ToolFailed(Exception):
    def __init__(self, tool, reason): super().__init__(f"{tool}: {reason}"); self.tool, self.reason = tool, reason
class TransientError(Exception): ...

# ---- output contracts (extra fields from untrusted services are dropped) ----
class PriceOut(BaseModel): prices: dict[str, int]; as_of: str; source: str; missing: list[str] = []; links: dict[str, str] = {}; retailers: dict[str, str] = {}; records: list[dict] = []
class StockOut(BaseModel): stock: dict[str, bool]; as_of: str; source: str; missing: list[str] = []; records: list[dict] = []
class BenchOut(BaseModel): relative_score: float; est_fps_1080p: float; source: str; records: list[dict] = []

@dataclass
class ToolSpec:
    out: type[BaseModel]; url_attr: str; path: str; field: str; permission: str = "read"

TOOLS: dict[str, ToolSpec] = {
    "price": ToolSpec(PriceOut, "price_service_url", "/v1/external/query", "price"),
    "stock": ToolSpec(StockOut, "stock_service_url", "/v1/external/query", "stock"),
    "benchmark": ToolSpec(BenchOut, "benchmark_service_url", "/v1/external/query", "benchmark"),
}
_breakers: dict[str, dict] = {}   # bulkhead: state is per tool
BREAKER_THRESHOLD, BREAKER_COOLDOWN = 3, 30.0

def reset_breakers(): _breakers.clear()
def _open(name) -> bool:
    b = _breakers.get(name)
    return bool(b and b["fails"] >= BREAKER_THRESHOLD and time.monotonic() - b["at"] < BREAKER_COOLDOWN)
def _record(name, ok):
    b = _breakers.setdefault(name, {"fails": 0, "at": 0.0})
    b["fails"] = 0 if ok else b["fails"] + 1; b["at"] = time.monotonic()

async def call_tool(state: AgentState, name: str, payload: dict) -> dict:
    spec = TOOLS.get(name)
    if spec is None or spec.permission != "read":
        raise ToolDenied(name)                                   # allowlist
    state.use_tool()
    if _open(name): raise ToolFailed(name, "circuit_open")
    url = getattr(settings, spec.url_attr)
    if not url:
        raise ToolFailed(name, "provider_not_configured")
    names = payload.get("names", [])
    request_payload = {"part_ids": names, "fields": [spec.field], "locale": state.request.locale}
    for attempt in range(3):
        timeout = min(settings.tool_timeout, state.time_left())
        if timeout <= 0: raise BudgetExceeded("time")
        try:
            async with httpx.AsyncClient(timeout=timeout) as c:
                r = await c.post(url + spec.path, json=request_payload,
                                 headers={"X-Internal-Token": settings.internal_token})
                if r.status_code >= 500: raise TransientError(f"HTTP {r.status_code}")
                r.raise_for_status(); response = r.json()
            health = response.get("provider_health", [])
            if not any(provider.get("healthy") for provider in health):
                raise ToolFailed(name, "provider_unavailable")
            if name == "price":
                listings = response.get("prices", [])
                values = {item["part_id"]: item["price"] for item in listings}
                data = {"prices": values, "as_of": max((item["fetched_at"] for item in listings), default=""),
                    "source": ", ".join(sorted({item["source"] for item in listings})),
                    "missing": sorted(set(names) - set(values)),
                    "links": {item["part_id"]: item["product_url"] for item in listings if item.get("product_url")},
                    "retailers": {item["part_id"]: item["retailer"] for item in listings},
                    "records": [{"kind": "price", "part_id": item["part_id"], "source": item["source"],
                         "authority": "retailer", "fetched_at": item["fetched_at"],
                         "observed_at": item["observed_at"], "expires_at": item["expires_at"],
                         "fields": {"price": item["price"]}} for item in listings]}
            elif name == "stock":
                listings = response.get("stock", [])
                values = {item["part_id"]: item["in_stock"] for item in listings}
                data = {"stock": values, "as_of": max((item["fetched_at"] for item in listings), default=""),
                    "source": ", ".join(sorted({item["source"] for item in listings})),
                    "missing": sorted(set(names) - set(values)),
                    "records": [{"kind": "stock", "part_id": item["part_id"], "source": item["source"],
                             "authority": "retailer", "fetched_at": item["fetched_at"],
                             "observed_at": item["observed_at"], "expires_at": item["expires_at"],
                             "fields": {"in_stock": item["in_stock"]}} for item in listings]}
            else:
                scores = response.get("benchmarks", [])
                if not scores: raise ToolFailed(name, "provider_unavailable")
                score = sum(item["performance_index"] for item in scores) / len(scores)
                fps = [item["game_fps_1080p"] for item in scores if item.get("game_fps_1080p") is not None]
                data = {"relative_score": score, "est_fps_1080p": sum(fps) / len(fps) if fps else 0.0,
                    "source": ", ".join(sorted({item["source"] for item in scores})),
                    "records": [{"kind": "benchmark", "part_id": item["part_id"], "source": item["source"],
                             "authority": "retailer", "fetched_at": item["fetched_at"],
                             "observed_at": item["observed_at"], "expires_at": item["expires_at"],
                             "fields": {"performance_index": item["performance_index"],
                                "game_fps_1080p": item.get("game_fps_1080p")}} for item in scores]}
            out = spec.out(**data).model_dump()                  # schema-validate untrusted output
            _record(name, True); return out
        except ToolFailed:
            _record(name, False); raise
        except (TransientError, httpx.TransportError, asyncio.TimeoutError) as e:
            if attempt == 2:
                _record(name, False); raise ToolFailed(name, type(e).__name__)
            await asyncio.sleep(settings.retry_base_delay * 2 ** attempt * (0.5 + random.random() / 2))  # backoff + jitter
        except (httpx.HTTPStatusError, ValueError) as e:         # permanent: no retry
            _record(name, False); raise ToolFailed(name, "bad_response")
