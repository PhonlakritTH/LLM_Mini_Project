# Module 04: External Data Services

## Status

**Partially live and active in the website flow.** Price lookup uses SerpApi's Google Shopping API. Stock, benchmark, and manufacturer-spec connectors currently return unavailable; they do not return synthetic success data.

## Endpoint

`POST /v1/external/query` requires `X-Internal-Token`. The request accepts `part_ids`, `fields` (`price`, `stock`, `benchmark`, `spec`), and locale. The response includes normalized records, provider health, coverage, and degraded status. `GET /health` is unauthenticated.

Price search uses Thai Google Shopping settings (`google.co.th`, `gl=th`, `hl=th`, Bangkok location), requires THB results with a title match, and returns the selected price, retailer, product URL, and fetch timestamps. Results may be absent when Google Shopping has no matching THB listing.

## Configuration and run

Copy `.env.example` to `.env`, set `SERPAPI_API_KEY`, and keep it private. Use the same `INTERNAL_TOKEN` as Module 03.

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8200 --reload
python -m pytest -q
```

Current provider tests: **5 passed**. Live provider behavior is tested with mocked HTTP responses; an actual SerpApi key is required for live queries.

## Remaining work

- Select and implement a licensed stock/availability source, benchmark source, and manufacturer-spec source.
- Improve product matching and expose multiple retailer offers instead of selecting one lowest matching listing.
- Add live integration tests that run only when provider credentials are explicitly configured.