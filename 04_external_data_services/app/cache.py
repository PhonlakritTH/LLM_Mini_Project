"""Short-term cache keyed by part_id/retailer/currency/schema_version. Stand-in for Redis."""
import time

class TTLCache:
    def __init__(self): self._store: dict[str, tuple[float, object]] = {}
    def key(self, *parts) -> str: return "|".join(str(p) for p in parts)
    def get(self, key: str):
        hit = self._store.get(key)
        if not hit: return None
        exp, val = hit
        if time.time() > exp:
            del self._store[key]; return None
        return val
    def set(self, key: str, val, ttl: int): self._store[key] = (time.time() + ttl, val)
    def clear(self): self._store.clear()

cache = TTLCache()
