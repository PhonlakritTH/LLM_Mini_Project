import time
_state: dict[str, dict] = {}
THRESHOLD, COOLDOWN = 3, 20.0
def reset(): _state.clear()
def is_open(name: str) -> bool:
    b = _state.get(name)
    return bool(b and b["fails"] >= THRESHOLD and time.monotonic() - b["at"] < COOLDOWN)
def record(name: str, ok: bool):
    b = _state.setdefault(name, {"fails": 0, "at": 0.0})
    b["fails"] = 0 if ok else b["fails"] + 1
    b["at"] = time.monotonic()
