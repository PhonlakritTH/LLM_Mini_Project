# Module 05: Data Integration

## Status

**Standalone service; not connected to the active website request path.** It accepts normalized records and produces a versioned part-catalog snapshot. It does not fetch Module 04 data itself.

## Endpoint and behavior

`POST /v1/integration/snapshot` requires `X-Internal-Token`. `GET /health` reports the canonical schema version.

The pipeline validates record kinds, quarantines invalid rows, removes exact duplicates, merges price/stock/benchmark/spec records, tracks source lineage, flags stale/conflicting/missing/out-of-stock data, and calculates coverage/completeness/quality scores. Snapshot state is returned by the request; there is no persistent catalog store or scheduled ingestion job.

## Run and tests

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8300 --reload
python -m pytest -q
```

Current test result: **5 passed, 1 failed**. `test_happy_path` uses observations dated 2026-09-27 while the configured price freshness limit is 900 seconds; when run on 2026-10-03 the pipeline correctly flags that price as stale, conflicting with the test's expectation that the part is not degraded.

## Remaining work

- Update time-sensitive test fixtures to use a controlled clock or fresh timestamps, then make the suite pass.
- Add an ingestion client that maps Module 04 responses to `RawRecord` and wire snapshots into Modules 03 and 06.
- Persist snapshots and define retention/version migration behavior.