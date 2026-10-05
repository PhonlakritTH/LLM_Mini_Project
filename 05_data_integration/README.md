# Module 05: Data Integration

## Status

**Active in the website request path.** Module 02 sends it the requested parts and normalized provider records carried by Module 03. It produces a versioned snapshot; it does not fetch Module 04 data itself and does not persist snapshots.

## Endpoint and behavior

`POST /v1/integration/snapshot` requires `X-Internal-Token`. `GET /health` reports the canonical schema version.

The pipeline validates record kinds, quarantines invalid rows, removes exact duplicates, merges price/stock/benchmark/spec records, tracks source lineage, flags stale/conflicting/missing/out-of-stock data, and calculates coverage/completeness/quality scores. Requested parts remain in the snapshot even when no provider record exists; their price and stock remain `null`. Owned parts are marked separately and excluded from purchase price coverage. Snapshot state is returned by the request; there is no persistent catalog store or scheduled ingestion job.

## Run and tests

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8300 --reload
python -m pytest -q
```

Current test result: **7 passed**, including fresh timestamp fixtures and no-provider requested-part behavior.

## Remaining work

- Add a controlled clock abstraction for deterministic freshness tests.
- Persist snapshots and define retention/version migration behavior.
- Persist snapshots and define retention/version migration behavior.