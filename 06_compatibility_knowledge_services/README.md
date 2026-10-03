# Module 06: Compatibility and Knowledge Services

## Status

**Standalone service; not connected to the active website request path.** It exposes compatibility assessment, retrieval, and alternatives behind one authenticated endpoint.

## Endpoint and current data

`POST /v1/knowledge/assess` requires `X-Internal-Token`; `GET /health` reports model/schema versions.

Compatibility uses deterministic safety rules for socket, PSU headroom, wattage limits, and case form factor. The RAG corpus is a small in-code set of sample manual/spec passages with keyword-overlap ranking; the configured embedding model is a placeholder, not a live vector embedding service. Alternative parts and prices come from a hard-coded substitution graph, not current catalog offers.

## Run and tests

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8400 --reload
python -m pytest -q
```

Current test result: **7 passed**.

## Remaining work

- Load verified manufacturer documents and versioned specs from a maintained source.
- Replace sample alternative prices with Module 05 catalog/Module 04 live offers.
- Connect the service to the agent and add evidence/provenance integration tests.