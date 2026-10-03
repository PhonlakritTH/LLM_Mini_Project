# Module 08: Recommendation and Feedback

## Status

**Standalone service; not connected to the active website request path.** It formats a decision into a user-facing response, accepts feedback, and routes unsafe reports to an in-memory safety queue.

## Endpoints and behavior

All endpoints require `X-Internal-Token` except health:

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/v1/recommendation/build` | Format a decision, limitations, setup steps, source references, and warranty contacts. |
| `POST` | `/v1/feedback` | Store pseudonymized feedback; unsafe feedback is added to the safety queue. |
| `GET` | `/v1/safety-queue` | Read the operator review queue. |
| `GET` | `/health` | Report service/schema health. |

Feedback, safety queue, and alert cooldown state are process-local memory. Live price alerts are disabled by default and no notification provider is configured. Warranty contacts are local directory data, not fetched from manufacturers at request time.

## Run and tests

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8600 --reload
python -m pytest -q
```

Current test result: **10 passed**.

## Remaining work

- Wire this service after Module 07 and expose the final response/feedback flow in the web app.
- Persist feedback and safety queue with access controls, retention jobs, and audit history.
- Add a real consent-aware notification provider and maintain verified warranty contacts.