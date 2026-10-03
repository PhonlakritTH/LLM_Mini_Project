# Module 03: PC Build AI Agent

## Status

**Active in the website request flow.** This FastAPI service runs a bounded, deterministic graph and is called by Module 02. It does not use a built-in mock fallback when a provider URL is missing or unavailable.

## Current graph

`classify -> extract -> ask_missing -> plan -> fetch -> integrate -> compatibility -> alternatives_rag -> quality -> package`

The planner currently selects from a small, fixed candidate list by use case and brand. Price, stock, and benchmark tools call Module 04's `/v1/external/query` contract. Price results and retailer links are preserved; missing records mark the result degraded. Compatibility rules are deterministic. The knowledge/RAG and alternative-build nodes are not connected yet and are explicitly reported as unavailable.

## Endpoint and run

`POST /v1/agent/run` requires `X-Internal-Token` and accepts an `AgentRequest`. It returns an `AgentResult` with an `evidence_package`, degraded-service list, trace, and request identifiers. `GET /health` reports the service and policy versions.

Configure `PRICE_SERVICE_URL`, `STOCK_SERVICE_URL`, and `BENCHMARK_SERVICE_URL` to Module 04; configure matching `INTERNAL_TOKEN` values in Modules 03 and 04.

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8100 --reload
python -m pytest -q
```

Current test result: **11 passed**.

## Remaining work

- Replace the fixed candidate list with catalog-backed candidate generation and budget optimization.
- Connect Module 05 snapshots and Module 06 compatibility/knowledge/alternative results.
- Add real benchmark and stock providers through Module 04.
