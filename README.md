# AI PC Spec Builder — Mini Project (Modules 01–08)

Build an intelligent PC-build assistant that analyzes a user's budget, use case, and existing parts, checks live prices, stock, and benchmarks, and produces an explainable, compatibility-checked build recommendation.

The system combines an AI agent, external price/stock/benchmark APIs, data integration, a local compatibility/value model, component-focused RAG, alternative-build analysis, deterministic decision rules, and an LLM-generated explanation inside a Docker-based architecture.

----

# Structure

```text
pc-spec-builder/
│
├── 01_web_app/                              # User-facing web and mobile interface
│   ├── 01_env.txt
│   ├── 02_step.txt
│   └── 03_process.txt
│
├── 02_api_backend/                          # Secure API and request-management layer
│   ├── 01_env.txt
│   ├── 02_step.txt
│   └── 03_process.txt
│
├── 03_pc_build_ai_agent/                    # Agent orchestration and tool selection
│   ├── 01_env.txt
│   ├── 02_step.txt
│   └── 03_process.txt
│
├── 04_external_data_services/               # Real-time price, stock, and benchmark adapters
│   ├── 01_env.txt
│   ├── 02_step.txt
│   └── 03_process.txt
│
├── 05_data_integration/                     # Multi-source part-catalog processing
│   ├── 01_env.txt
│   ├── 02_step.txt
│   └── 03_process.txt
│
├── 06_compatibility_knowledge_services/     # Compatibility/value prediction, Component RAG, alternative builds
│   ├── 01_env.txt
│   ├── 02_step.txt
│   └── 03_process.txt
│
├── 07_decision_llm_engine/                  # Build decision and natural-language explanation
│   ├── 01_env.txt
│   ├── 02_step.txt
│   └── 03_process.txt
│
└── 08_recommendation_feedback/              # Final recommendation, alerts, and continuous feedback loop
    ├── 01_env.txt
    ├── 02_step.txt
    └── 03_process.txt
```

# Core Recommendations

The system produces one primary action based on the assessed compatibility, price/stock conditions, benchmark performance, and available alternatives:

- **Finalize build** — Parts are compatible, within budget, and in stock.
- **Swap component** — A clearly better or cheaper compatible alternative is available.
- **Wait for price drop** — Price is high relative to trend, or a part is temporarily out of stock with no good alternative.
- **Avoid this combination** — The parts are incompatible (e.g. wrong socket, insufficient PSU) with no safe alternative.
- **Setup instructions** — Verification steps (e.g. confirm PSU wattage before checkout) and manufacturer support contacts.

Every recommendation should include its compatibility status, confidence, reasons, alternative parts, source citations, data freshness, and any unavailable or degraded services.

----

## How to Run

This repository is currently at the **design and documentation stage**. Each `01-08` folder contains planning files, not runnable source code yet.

Once implemented, use **Docker Compose** as the main system orchestrator for managing and connecting all services.

* **`docker-compose.yml`** — defines and connects all services.
* **`Dockerfile`** — defines the environment and dependencies for each service.
* **`.env`** — stores API keys and private configuration.
* **Docker Network** — enables communication between containers.
* **`Makefile`** *(optional)* — provides shortcuts such as `make up`, `make down`, `make logs`, and `make rebuild`.

Start the complete system with:

```bash
docker compose up -d
```

**Docker Compose is the main orchestrator for the complete system.**

## Summary

This project is designed as an end-to-end architecture for an explainable, real-time PC-build assistant. **Modules 01–03** manage user interaction, secure API access, intent understanding, planning, and AI-agent orchestration. **Modules 04–05** collect and normalize live price, stock, and benchmark data into a versioned part-catalog snapshot.

**Module 06** evaluates build compatibility and value with a local ML/DL model, retrieves verified component knowledge through Component RAG, and identifies alternative parts. **Module 07** applies deterministic decision rules to select the final action before using an LLM to produce a grounded natural-language explanation. **Module 08** delivers the recommendation, supports follow-up questions and build updates, and captures governed feedback for evaluation and future system improvements.

The architecture keeps safety-critical decisions (compatibility, wattage, budget) separate from free-form LLM generation. Official spec sheets, part availability, model versions, source provenance, data freshness, fallback behavior, and decision traces remain visible and auditable throughout the workflow.

----

## Concept mapping (from the original travel-assistant version)

| Original (Travel Assistant)                     | Adapted (PC Spec Builder)                                          |
|--------------------------------------------------|----------------------------------------------------------------------|
| TravelRequest                                     | BuildRequest (budget, use_case, preferred_brand, existing_parts)     |
| risk_level                                        | compatibility_status                                                  |
| Weather / Transport / Disaster API                | Price API / Stock-Availability API / Benchmark API                   |
| Route / RouteCandidate                            | Alternative build / component swap suggestion                        |
| Local Risk Model                                  | Compatibility/Value Model                                             |
| Disaster RAG                                      | Component RAG (specs, manuals, driver requirements)                  |
| Decision Agent                                    | Build Decision Agent (budget + performance + compatibility rules)    |
| travel normally / change route / delay / avoid    | finalize build / swap component / wait for price drop / avoid combination |
| emergency instructions / official contacts        | setup/verification steps / manufacturer support contacts             |
