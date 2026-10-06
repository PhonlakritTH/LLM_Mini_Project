# Run the PC Spec Builder

This guide starts the existing services. It does **not** make unavailable product data live. For the real-data implementation order and current gaps, read the root [README.md](README.md).

## Requirements

- Node.js 20.9+ and npm
- Python with versions supported by the individual `requirements.txt` files
- Docker Desktop/Engine for the Docker option
- SerpApi key for the only currently implemented live data connector: Google Shopping price search

Without `SERPAPI_API_KEY`, the web app/API may start but price lookup is unavailable and recommendations are degraded. The agent currently selects from a fixed in-code candidate list; a SerpApi result does not verify that list against a canonical catalog. A key also does not provide verified stock, manufacturer specs, or benchmarks. Treat degraded output as unverified planning, not a purchase quote.

## Run with Docker Compose

At the repository root, copy `.env.example` to `.env` and put the SerpApi key in the root `.env`:

```text
SERPAPI_API_KEY=your-private-key
```

Keep `.env` private; do not commit it. This root variable is interpolated by Compose for Module 04. The Compose file currently loads the checked-in per-service `.env.example` files for other defaults and sets internal service URLs/tokens itself.

Start Docker Engine, then from the repository root run:

```powershell
docker compose up --build -d
docker compose ps
```

Open `http://localhost:3000`. Service `depends_on` controls start order only; it does not wait for application readiness. If a request is initially degraded, check the service status/logs and retry after the services are ready:

```powershell
docker compose logs --tail 100
```

Stop the stack with `docker compose down`. This does not persist the in-memory catalog, rate limit, feedback, or snapshot state.

## Run services locally (Windows PowerShell)

Open a separate terminal for each service. Copy each relevant `.env.example` to `.env` in that module before starting it; local processes read the module `.env` files. Use the same `INTERNAL_TOKEN` for Modules 02, 03, and 04. Do not put private credentials in frontend `NEXT_PUBLIC_*` variables.

Start data and downstream services first:

```powershell
Set-Location 04_external_data_services
Copy-Item .env.example .env
# Add SERPAPI_API_KEY to this local .env
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8200 --reload
```

```powershell
Set-Location 05_data_integration
Copy-Item .env.example .env
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8300 --reload
```

```powershell
Set-Location 06_compatibility_knowledge_services
Copy-Item .env.example .env
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8400 --reload
```

```powershell
Set-Location 07_decision_llm_engine
Copy-Item .env.example .env
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8500 --reload
```

```powershell
Set-Location 08_recommendation_feedback
Copy-Item .env.example .env
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8600 --reload
```

Then start the agent and API. In `03_pc_build_ai_agent/.env`, point the three data URLs at Module 04 and set the shared internal token. In `02_api_backend/.env`, point the service URLs at the local ports below and use the same internal token.

```powershell
Set-Location 03_pc_build_ai_agent
Copy-Item .env.example .env
# Set PRICE_SERVICE_URL, STOCK_SERVICE_URL, BENCHMARK_SERVICE_URL to http://localhost:8200
# Keep INTERNAL_TOKEN equal to the values in Modules 02 and 04
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8100 --reload
```

```powershell
Set-Location 02_api_backend
Copy-Item .env.example .env
# Set AGENT_SERVICE_URL=http://localhost:8100
# Set DATA_INTEGRATION_SERVICE_URL=http://localhost:8300
# Set KNOWLEDGE_SERVICE_URL=http://localhost:8400
# Set DECISION_SERVICE_URL=http://localhost:8500
# Set RECOMMENDATION_SERVICE_URL=http://localhost:8600
# Keep INTERNAL_TOKEN equal to the values in Modules 03 and 04
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000 --reload
```

Finally, start the website:

```powershell
Set-Location 01_web_app
npm ci
npm run dev
```

Module 01 uses `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` by default. Override it in `01_web_app/.env.local` only when the API is at another address. Open `http://localhost:3000`.

## Check service availability

Open these health URLs after startup. A healthy process does not guarantee that its external data source is healthy.

| Module | Port | Health/docs |
|---|---:|---|
| 01 Web App | 3000 | `http://localhost:3000` |
| 02 API Backend | 8000 | `http://localhost:8000/health`, `/ready`, `/docs` |
| 03 PC Build AI Agent | 8100 | `http://localhost:8100/health` |
| 04 External Data | 8200 | `http://localhost:8200/health` |
| 05 Data Integration | 8300 | `http://localhost:8300/health` |
| 06 Compatibility/Knowledge | 8400 | `http://localhost:8400/health` |
| 07 Decision/LLM | 8500 | `http://localhost:8500/health` |
| 08 Recommendation/Feedback | 8600 | `http://localhost:8600/health` |

Use the website form for an end-to-end request. A `degraded` response or `null` price/stock means the source could not verify that field; it is not a zero price, an in-stock signal, or a fully verified build. For provider checks and unit tests, see each module README.
