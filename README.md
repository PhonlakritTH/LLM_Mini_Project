# AI PC Spec Builder

**Repository status: 2026-10-05.** The website request now orchestrates Modules 02–08. Real external inputs are still incomplete: price lookup requires SerpApi, and stock/benchmark providers are unavailable. When a provider is unavailable, the app reports degraded status and keeps the value unknown instead of inserting sample data.

## Current status

The active request path is:

`01_web_app -> 02_api_backend -> 03_pc_build_ai_agent -> 04_external_data_services -> 05_data_integration -> 06_compatibility_knowledge_services -> 07_decision_llm_engine -> 08_recommendation_feedback`

The agent gathers available external records; the backend sends requested parts and those records through snapshot integration, compatibility assessment, deterministic decision rules, and final response formatting. The local end-to-end smoke test passed without API keys: the response was degraded, recommended waiting, and preserved unknown prices/stock as `null`.

Price lookup uses SerpApi Google Shopping when `SERPAPI_API_KEY` is provided. Stock, benchmark, manufacturer specs, RAG documents, and alternatives do not currently have live providers. Module 06 therefore returns deterministic compatibility results while marking RAG and alternatives unavailable. Module 07's LLM client remains a fixed-template fallback even if a key is configured. Module 08 formats the result; its feedback endpoints are not yet called by the website.

## Module status

| Module | Current status |
|---|---|
| [01 Web App](01_web_app/README.md) | Active form/results UI; handles unknown and partial data. |
| [02 API Backend](02_api_backend/README.md) | Active auth, request forwarding, and orchestration through Modules 05–08. Development auth/state are in-memory. |
| [03 PC Build AI Agent](03_pc_build_ai_agent/README.md) | Active deterministic planner/checks; fixed candidate list; calls Module 04 and forwards records to Module 05 via the backend. |
| [04 External Data Services](04_external_data_services/README.md) | Live price search through SerpApi; stock/benchmark/spec providers unavailable. |
| [05 Data Integration](05_data_integration/README.md) | Active snapshot stage; retains requested parts when providers return no records; snapshots are not persisted. |
| [06 Compatibility and Knowledge](06_compatibility_knowledge_services/README.md) | Active deterministic compatibility rules; sample RAG/alternatives are disabled and reported unavailable. |
| [07 Decision and LLM Engine](07_decision_llm_engine/README.md) | Active deterministic action selection; LLM call is still a placeholder and uses a fixed explanation. |
| [08 Recommendation and Feedback](08_recommendation_feedback/README.md) | Active final response formatter; feedback endpoints exist but are not wired to the web UI. |

## What to do next

1. Add a SerpApi key locally and verify price matches, source links, and query limits against Thai listings.
2. Choose licensed live providers for stock, benchmarks, and manufacturer specifications; keep unavailable states until validated.
3. Replace Module 06's sample RAG/catalog with verified sources and a real retrieval/alternative provider.
4. Implement the Module 07 LLM client or explicitly keep the deterministic explanation-only mode; a configured key currently does not make a request.
5. Wire the website to Module 08 feedback and add user consent/retention behavior.
6. Before public deployment, replace development-token auth and in-memory rate-limit/idempotency/feedback state with production identity and persistent stores.

## Verification snapshot

| Area | Last checked result |
|---|---|
| Module 02 | 7 tests passed |
| Module 03 | 11 tests passed |
| Module 04 | 5 tests passed |
| Module 05 | 7 tests passed |
| Module 06 | 8 tests passed |
| Module 07 | 10 tests passed |
| Module 08 | 11 tests passed |
| Web app | Production build passed; `npm audit` reported 0 vulnerabilities. |

All Python Module test suites passed when run separately. The no-key end-to-end request through Modules 02–08 returned degraded status with unknown prices/stock preserved. Docker Compose configuration validates; Docker Engine was unavailable for a container startup check. See [README_RUN.md](README_RUN.md) for startup instructions and [README_01_02.md](README_01_02.md) for the web/API quick reference.
