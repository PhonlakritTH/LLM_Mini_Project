# Module 02: API Backend

## Status

**Active in the website request flow.** This FastAPI service authenticates web requests, applies a development rate limit, forwards the build request to Module 03, and adapts the agent evidence package to the web response schema.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/v1/auth/dev-token` | Issues a short-lived development JWT; not production authentication. |
| `POST` | `/v1/builder/recommendations` | Authenticated build request; calls Module 03 and returns recommendation/evidence fields. |
| `GET` | `/health`, `/ready` | Process health and readiness probes. |

The backend returns HTTP 503 when Module 03 cannot be reached. It does not fall back to sample recommendation data. Missing prices, stock, and benchmark values remain unknown in the response.

## Configuration and run

Copy `.env.example` to `.env`. Set `AGENT_SERVICE_URL` to Module 03 and use the same `INTERNAL_TOKEN` in both services.

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000 --reload
```

Run tests with `python -m pytest -q` from this folder. Current result: **5 passed**.

## Remaining work

- Replace `/v1/auth/dev-token` with OAuth2/OIDC before public deployment.
- Move rate-limit and idempotency state out of process memory for multi-instance operation.
- Add an HTTP-level integration test against a running Module 03 service.