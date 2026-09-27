"""Price/stock alert dedup + cooldown, consent-gated."""
import time
from .config import settings
_last_sent: dict[str, float] = {}

def reset(): _last_sent.clear()

def should_send(user_id: str, part_id: str, consent: bool) -> bool:
    if not consent: return False
    key = f"{user_id}:{part_id}"
    now = time.time()
    if now - _last_sent.get(key, 0) < settings.alert_cooldown_seconds:
        return False
    _last_sent[key] = now
    return True
