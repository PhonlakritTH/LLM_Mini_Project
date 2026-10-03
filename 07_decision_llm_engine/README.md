# Module 07: Decision and LLM Engine

## Status

**Standalone service; not connected to the active website request path.** The deterministic decision rules are implemented, but the LLM call is still a placeholder.

## Endpoint and behavior

`POST /v1/decision/evaluate` requires `X-Internal-Token` and supports the configured locale list. It applies hard compatibility overrides, budget, stock uncertainty, alternatives, and price signals before generating an explanation. The action is locked before explanation validation; invalid/tampered output falls back to a fixed template.

Important: `call_llm()` currently returns `None` even when `LLM_API_KEY` is set. No provider request is made, so the response uses the fixed template and marks `fallback_used=true`. `GET /health` reports the policy version.

## Run and tests

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8500 --reload
python -m pytest -q
```

Current test result: **9 passed**.

## Remaining work

- Implement a real structured-output LLM client with timeout, key handling, and provider error tests.
- Consume Module 05/06 evidence and connect the locked decision to Module 08.
- Keep deterministic safety rules authoritative and validate explanations against real citations.