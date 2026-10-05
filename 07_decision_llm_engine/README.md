# Module 07: Decision and LLM Engine

## Status

**Active in the website request path.** Deterministic decision rules consume Module 05/06 output. The LLM call is still a placeholder, so explanations use the fixed template.

## Endpoint and behavior

`POST /v1/decision/evaluate` requires `X-Internal-Token` and supports the configured locale list. It applies hard compatibility overrides, budget, stock uncertainty, alternatives, and price signals before generating an explanation. The action is locked before explanation validation; invalid/tampered output falls back to a fixed template.

Important: `call_llm()` currently returns `None` even when `LLM_API_KEY` is set. No provider request is made, so the response uses the fixed template and marks `fallback_used=true`. Missing prices are not summed as a zero total; the decision waits and explains that budget comparison is unavailable. `GET /health` reports the policy version.

## Run and tests

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8500 --reload
python -m pytest -q
```

Current test result: **10 passed**.

## Remaining work

- Implement a real structured-output LLM client with timeout, key handling, and provider error tests.
- Implement a real structured-output LLM client with timeout, key handling, and provider error tests.
- Keep deterministic safety rules authoritative and validate explanations against real citations.