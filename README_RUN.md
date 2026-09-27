# Running the full pc-spec-builder stack

Each module 02-08 is a standalone FastAPI service; 01 is the Next.js web app.
This build stage wires every service together with mocked external calls
(no real Postgres/Redis/Kafka/LLM key needed) so the whole flow runs and
is testable end-to-end without paid dependencies.

## Quick start (Docker)
    docker compose up -d      # or: make up
    open http://localhost:3000

## Quick start (no Docker, one terminal per service)
    (cd 01_web_app && npm install && cp .env.example .env.local && npm run dev)              # :3000
    (cd 02_api_backend && pip install -r requirements.txt && cp .env.example .env && uvicorn app.main:app --port 8000 --reload)
    (cd 03_pc_build_ai_agent && pip install -r requirements.txt && cp .env.example .env && uvicorn app.main:app --port 8100 --reload)
    (cd 04_external_data_services && pip install -r requirements.txt && cp .env.example .env && uvicorn app.main:app --port 8200 --reload)
    (cd 05_data_integration && pip install -r requirements.txt && cp .env.example .env && uvicorn app.main:app --port 8300 --reload)
    (cd 06_compatibility_knowledge_services && pip install -r requirements.txt && cp .env.example .env && uvicorn app.main:app --port 8400 --reload)
    (cd 07_decision_llm_engine && pip install -r requirements.txt && cp .env.example .env && uvicorn app.main:app --port 8500 --reload)
    (cd 08_recommendation_feedback && pip install -r requirements.txt && cp .env.example .env && uvicorn app.main:app --port 8600 --reload)

## Run all tests
    make test

## Port map
| Module | Service                     | Port |
|--------|------------------------------|------|
| 01     | web_app (Next.js)            | 3000 |
| 02     | api_backend                  | 8000 |
| 03     | pc_build_agent                | 8100 |
| 04     | external_data_services        | 8200 |
| 05     | data_integration               | 8300 |
| 06     | compat_knowledge_services      | 8400 |
| 07     | decision_llm_engine             | 8500 |
| 08     | recommendation_feedback         | 8600 |

## Data flow (matches the README diagram)
    Web App -> API/Backend -> PC Build AI Agent
      -> [parallel] External Data Services (price/stock/benchmark)
      -> Data Integration (canonical PartCatalogSnapshot)
      -> Compatibility & Knowledge Services (compat score + RAG + alternatives)
      -> Decision & LLM Engine (locked action_code + explanation)
      -> Recommendation & Feedback (final response shown in Web App; feedback loop)

## Known simplifications (documented, not hidden)
- Postgres/Redis/Kafka are replaced with in-memory stores everywhere (clearly labeled "stand-in for X" in code comments).
  Swapping in real infra means changing only the storage layer, not the service contracts.
- Module 03/04/06 external calls (LLM planner, retailer APIs, embeddings) use built-in deterministic mocks
  when their *_SERVICE_URL / *_API_KEY env vars are empty, so the whole system runs offline.
- Module 07's `LLM_API_KEY` is empty by default, so it always uses the fixed fallback explanation template
  (this is by design in the module 07 spec: "Use a fixed fallback template when the LLM is unavailable").
- End-to-end wiring between services (02 calling 03, 03 calling 04-06, decision calling 08) uses the *_SERVICE_URL
  env vars set in docker-compose.yml; when run without Docker, set them by hand or keep them empty to use mocks.
