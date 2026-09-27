"""Explicit feedback stored separately from telemetry; unsafe reports go to a human safety queue.
System never learns directly from live feedback — only reviewed batches feed retraining."""
import uuid
from datetime import datetime, timedelta, timezone
from .config import settings
from .models import Feedback, FeedbackReceipt, pseudonymize, now_iso

STORE: list[dict] = []          # stand-in for PostgreSQL, respects retention_days
SAFETY_QUEUE: list[dict] = []   # stand-in for an operator alert queue

def submit(fb: Feedback) -> FeedbackReceipt:
    pid = pseudonymize(fb.user_id)
    now = datetime.now(timezone.utc)
    record = {"feedback_id": uuid.uuid4().hex, "pseudonymous_id": pid, "request_id": fb.request_id,
              "category": fb.category, "comment": fb.comment[:500], "stored_at": now.isoformat(),
              "expires_at": (now + timedelta(days=settings.feedback_retention_days)).isoformat(), "reviewed": False}
    STORE.append(record)
    routed = fb.category == "unsafe"
    if routed:
        SAFETY_QUEUE.append({**record, "alerted_at": now_iso()})
    return FeedbackReceipt(feedback_id=record["feedback_id"], pseudonymous_id=pid, stored_at=record["stored_at"],
                           routed_to_safety_review=routed)

def purge_expired():
    now = datetime.now(timezone.utc).isoformat()
    STORE[:] = [r for r in STORE if r["expires_at"] > now]

def reviewed_for_training() -> list[dict]:
    return [r for r in STORE if r["reviewed"]]   # only reviewed rows are eligible; live feedback alone never trains the model
