# Module 08: Recommendation and Feedback

## Status

**Partially active in the website request path.** Module 02 sends Module 07's decision here for final formatting. Feedback and safety-queue endpoints remain separate and are not yet called from the website.

## Endpoints and behavior

All endpoints require `X-Internal-Token` except health:

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/v1/recommendation/build` | Format a decision, limitations, setup steps, source references, and warranty contacts. |
| `POST` | `/v1/feedback` | Store pseudonymized feedback; unsafe feedback is added to the safety queue. |
| `GET` | `/v1/safety-queue` | Read the operator review queue. |
| `GET` | `/health` | Report service/schema health. |

Feedback, safety queue, and alert cooldown state are process-local memory. Live price alerts are disabled by default and no notification provider is configured. Placeholder warranty numbers were removed; no contacts are returned until a verified directory is configured. Null prices and purchase links are preserved in the formatted parts.

## Run and tests

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8600 --reload
python -m pytest -q
```

Current test result: **11 passed**.

## Remaining work

- Wire the feedback endpoint to the web UI with consent and abuse controls.
- Persist feedback and safety queue with access controls, retention jobs, and audit history.
- Add a real consent-aware notification provider and maintain verified warranty contacts.