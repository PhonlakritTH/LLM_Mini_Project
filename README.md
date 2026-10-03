# AI PC Spec Builder

**Repository status: 2026-10-03.** The website and request path are implemented through live price search and deterministic compatibility checks. The full eight-module architecture is not yet integrated; this README distinguishes the running path from standalone services and planned work.

## Current status

The active request path is:

`01_web_app -> 02_api_backend -> 03_pc_build_ai_agent -> 04_external_data_services -> SerpApi Google Shopping`

The app displays candidate parts, matched THB prices, and retailer links when available. Without `SERPAPI_API_KEY`, or when no listing matches a part, it preserves unknown values and returns a degraded recommendation rather than fake prices. Stock, benchmark, and manufacturer-spec data have no live provider configured. The active agent does not yet call Modules 05–08.

## Module status

| Module | Current status |
|---|---|
| [01 Web App](01_web_app/README.md) | Active form/results UI; handles unknown and partial data. |
| [02 API Backend](02_api_backend/README.md) | Active auth, rate limit, request forwarding, and response adaptation. Development auth/state are in-memory. |
| [03 PC Build AI Agent](03_pc_build_ai_agent/README.md) | Active deterministic planner/checks; fixed candidate list; calls Module 04. |
| [04 External Data Services](04_external_data_services/README.md) | Live price search through SerpApi; stock/benchmark/spec providers unavailable. |
| [05 Data Integration](05_data_integration/README.md) | Standalone snapshot pipeline; not in the active flow. One freshness-sensitive test currently fails. |
| [06 Compatibility and Knowledge](06_compatibility_knowledge_services/README.md) | Standalone rules service; RAG corpus and alternatives are sample in-code data; not in the active flow. |
| [07 Decision and LLM Engine](07_decision_llm_engine/README.md) | Standalone deterministic rules; LLM client is still a placeholder; not in the active flow. |
| [08 Recommendation and Feedback](08_recommendation_feedback/README.md) | Standalone formatter/feedback service with in-memory state; not in the active flow. |

## What to do next

1. Add a SerpApi key locally and verify price matches, source links, and query limits against Thai listings.
2. Choose licensed live providers for stock, benchmarks, and manufacturer specs; keep each unavailable until implemented and validated.
3. Fix Module 05's stale test fixture, then wire its snapshots into the agent.
4. Replace Module 06 sample documents/catalog with verified, versioned sources and connect its assessment, RAG, and alternatives.
5. Implement the Module 07 LLM client (a configured key currently does not make an LLM request), then connect Modules 07 and 08 to the active response flow.
6. Before public deployment, replace development-token auth and in-memory rate-limit/idempotency/feedback state with production identity and persistent stores.

## Verification snapshot

| Area | Last checked result |
|---|---|
| Module 02 | 5 tests passed |
| Module 03 | 11 tests passed |
| Module 04 | 5 tests passed |
| Module 05 | 5 passed, 1 failed: fixture dated 2026-09-27 is older than the 900-second price freshness limit on the check date. |
| Module 06 | 7 tests passed |
| Module 07 | 9 tests passed |
| Module 08 | 10 tests passed |
| Web app | Production build passed; `npm audit` reported 0 vulnerabilities. |

Docker Compose configuration validates, but Docker Engine was unavailable during the last startup attempt. Modules 02–04 and the website were smoke-tested as local processes. See [README_RUN.md](README_RUN.md) for startup instructions and [README_01_02.md](README_01_02.md) for the web/API quick reference.
