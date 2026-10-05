# Module 02: API Backend

## Status

**Active in the website request flow.** This FastAPI service authenticates web requests, applies a development rate limit, calls Module 03, then orchestrates Modules 05–08 and maps the final result to the web response schema.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/v1/auth/dev-token` | Issues a short-lived development JWT; not production authentication. |
| `POST` | `/v1/builder/recommendations` | Authenticated build request; calls Module 03 and returns recommendation/evidence fields. |
| `GET` | `/health`, `/ready` | Process health and readiness probes. |

The backend returns HTTP 503 when Module 03 cannot be reached. If a downstream module fails, it returns a degraded `wait_for_price_drop` response (unless a hard incompatibility is known). It does not fall back to sample recommendation data. Missing prices, stock, and benchmark values remain unknown in the response.

## Configuration and run

Copy `.env.example` to `.env`. Set URLs for Modules 03 and 05–08, and use the same `INTERNAL_TOKEN` across internal services.

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000 --reload
```

Run tests with `python -m pytest -q` from this folder. Current result: **7 passed**, including downstream ordering, unknown-price preservation, and failure degradation.

## Remaining work

- Replace `/v1/auth/dev-token` with OAuth2/OIDC before public deployment.
- Move rate-limit and idempotency state out of process memory for multi-instance operation.
- Replace development-token auth with OAuth2/OIDC before public deployment.
- Move rate-limit and idempotency state out of process memory for multi-instance operation.
- Add persistent request tracing and a full live-provider integration test.