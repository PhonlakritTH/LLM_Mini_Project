# Module 06: Compatibility and Knowledge Services

## Status

**Active in the website request path.** Module 02 sends it the Module 05 snapshot. Deterministic compatibility rules run; RAG and alternative data are disabled by default and reported unavailable.

## Endpoint and current data

`POST /v1/knowledge/assess` requires `X-Internal-Token`; `GET /health` reports model/schema versions.

Compatibility uses deterministic safety rules for socket, PSU headroom, wattage limits, and case form factor. Sample RAG passages and hard-coded alternative prices are not returned in the default request path. Until verified documents and a current catalog/provider are configured, the response returns empty evidence/alternatives and degraded-service flags.

## Run and tests

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8400 --reload
python -m pytest -q
```

Current test result: **8 passed**.

## Remaining work

- Load verified manufacturer documents and versioned specs from a maintained source.
- Replace sample alternative prices with Module 05 catalog/Module 04 live offers.
- Add verified, versioned documents and live/catalog-backed alternatives, then enable each capability only after source validation.