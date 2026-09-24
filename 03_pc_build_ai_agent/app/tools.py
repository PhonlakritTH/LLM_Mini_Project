"""Allowlisted tools: fixed JSON contract, timeout, permission, error contract, retry, circuit breaker."""
import asyncio, random, time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Optional
import httpx
from pydantic import BaseModel
from .config import settings
from .state import AgentState, BudgetExceeded

class ToolDenied(Exception): ...
class ToolFailed(Exception):
    def __init__(self, tool, reason): super().__init__(f"{tool}: {reason}"); self.tool, self.reason = tool, reason
class TransientError(Exception): ...

# ---- output contracts (extra fields from untrusted services are dropped) ----
class PriceOut(BaseModel): prices: dict[str, int]; as_of: str; source: str
class StockOut(BaseModel): stock: dict[str, bool]; as_of: str; source: str
class BenchOut(BaseModel): relative_score: float; est_fps_1080p: float; source: str
class RagOut(BaseModel): notes: list[dict]
class AltOut(BaseModel): alternatives: list[dict]

PRICES = {"Ryzen 5 7600": 7500, "Core i5-13400F": 7900, "Ryzen 7 7700": 11500, "Core i7-13700": 13500, "Ryzen 5 5600G": 5500,
          "Core i3-12100": 4200, "Core i5-13600K": 11900, "Ryzen 9 7900": 17500, "Core i7-13700K": 14900,
          "RTX 4060": 10500, "RX 7600": 8900, "RTX 4060 Ti": 15500, "RX 7700 XT": 14500, "RTX 4070 Super": 25500, "RX 7800 XT": 19500,
          "Integrated": 0, "B650M": 3900, "B550M": 3200, "B760M": 3600, "16GB DDR5": 2200, "16GB DDR4": 1800,
          "1TB NVMe": 2200, "650W 80+ Bronze": 1900, "ATX Mid Tower": 1500}
DOWNGRADE = {"RTX 4060 Ti": "RTX 4060", "RTX 4070 Super": "RTX 4060 Ti", "RTX 4060": "RX 7600", "RX 7700 XT": "RX 7600", "RX 7800 XT": "RX 7700 XT"}

def _now(): return datetime.now(timezone.utc).isoformat()
def _maybe_fail(tool):
    if tool in settings.mock_fail.split(","): raise TransientError(f"{tool} mock outage")

async def _price(p): _maybe_fail("price"); return {"prices": {n: PRICES.get(n, 0) for n in p["names"]}, "as_of": _now(), "source": "mock-retailer"}
async def _stock(p): _maybe_fail("stock"); return {"stock": {n: True for n in p["names"]}, "as_of": _now(), "source": "mock-stock"}
async def _bench(p):
    _maybe_fail("benchmark")
    s = {"gaming": 85, "video_editing": 78, "office": 60, "streaming": 80, "ai_rendering": 88}[p["use_case"]]
    return {"relative_score": float(s), "est_fps_1080p": round(s * 1.4, 1), "source": "mock-benchmark"}
async def _rag(p): return {"notes": [{"text": f"Check the power connectors of {p['gpu']} against your PSU.", "source": "mock-spec-sheet"}]}
async def _alt(p):
    d = DOWNGRADE.get(p["gpu"])
    return {"alternatives": [{"type": "gpu", "name": d, "price": PRICES[d], "saves": PRICES[p["gpu"]] - PRICES[d]}] if d else []}

@dataclass
class ToolSpec:
    out: type[BaseModel]; url_attr: str; path: str; mock: Callable; permission: str = "read"

TOOLS: dict[str, ToolSpec] = {
    "price": ToolSpec(PriceOut, "price_service_url", "/v1/prices", _price),
    "stock": ToolSpec(StockOut, "stock_service_url", "/v1/stock", _stock),
    "benchmark": ToolSpec(BenchOut, "benchmark_service_url", "/v1/benchmarks", _bench),
    "component_rag": ToolSpec(RagOut, "rag_service_url", "/v1/rag/query", _rag),
    "alternatives": ToolSpec(AltOut, "alternatives_service_url", "/v1/alternatives", _alt),
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
    for attempt in range(3):
        timeout = min(settings.tool_timeout, state.time_left())
        if timeout <= 0: raise BudgetExceeded("time")
        try:
            if url:                                              # fixed URL from config only
                async with httpx.AsyncClient(timeout=timeout) as c:
                    r = await c.post(url + spec.path, json=payload)
                    if r.status_code >= 500: raise TransientError(f"HTTP {r.status_code}")
                    r.raise_for_status(); data = r.json()
            else:
                data = await asyncio.wait_for(spec.mock(payload), timeout)
            out = spec.out(**data).model_dump()                  # schema-validate untrusted output
            _record(name, True); return out
        except (TransientError, httpx.TransportError, asyncio.TimeoutError) as e:
            if attempt == 2:
                _record(name, False); raise ToolFailed(name, type(e).__name__)
            await asyncio.sleep(settings.retry_base_delay * 2 ** attempt * (0.5 + random.random() / 2))  # backoff + jitter
        except (httpx.HTTPStatusError, ValueError) as e:         # permanent: no retry
            _record(name, False); raise ToolFailed(name, "bad_response")
