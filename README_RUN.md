# Run the PC Spec Builder

The active website flow uses Modules 01–04 only. Modules 05–08 can run independently, but are not yet called by the website/agent path. Current capability details and priorities are in [README.md](README.md).

## Requirements

- Node.js 20.9 or newer and npm
- Python 3.12 (or a compatible version for the service requirements)
- Docker Desktop/Engine only for the Docker route
- A SerpApi key for live Google Shopping price lookup

Without `SERPAPI_API_KEY`, the website still runs but reports price data as unavailable. Stock, benchmarks, and manufacturer specs remain unavailable until providers are implemented.

## Docker

Copy the root `.env.example` to `.env`, add the key, and keep `.env` private:

```text
SERPAPI_API_KEY=your-private-key
```

Start Docker Engine, then run from the repository root:

```powershell
docker compose up --build -d
```

Open `http://localhost:3000`. Stop the stack with `docker compose down`.

## Local processes (Windows PowerShell)

First copy each service's `.env.example` to `.env` and configure:

- `04_external_data_services/.env`: `SERPAPI_API_KEY` and `INTERNAL_TOKEN=dev-internal`.
- `03_pc_build_ai_agent/.env`: `PRICE_SERVICE_URL`, `STOCK_SERVICE_URL`, and `BENCHMARK_SERVICE_URL` set to `http://localhost:8200`; set the same internal token.
- `02_api_backend/.env`: `AGENT_SERVICE_URL=http://localhost:8100` and the same internal token.
- Module 01 uses `http://localhost:8000` by default; set `NEXT_PUBLIC_API_BASE_URL` in `.env.local` only when changing that address.

Start each command in its own terminal, in this order:

```powershell
Set-Location 04_external_data_services
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8200 --reload
```

```powershell
Set-Location 03_pc_build_ai_agent
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8100 --reload
```

```powershell
Set-Location 02_api_backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000 --reload
```

```powershell
Set-Location 01_web_app
npm ci
npm run dev
```

Open `http://localhost:3000`. For Modules 05–08 standalone startup instructions, see their module READMEs.

## Ports and endpoints

| Module | Port | Main endpoint |
|---|---:|---|
| 01 Web App | 3000 | Browser UI |
| 02 API Backend | 8000 | `POST /v1/builder/recommendations` |
| 03 PC Build AI Agent | 8100 | `POST /v1/agent/run` |
| 04 External Data Services | 8200 | `POST /v1/external/query` |
| 05 Data Integration | 8300 | `POST /v1/integration/snapshot` |
| 06 Compatibility/Knowledge | 8400 | `POST /v1/knowledge/assess` |
| 07 Decision/LLM | 8500 | `POST /v1/decision/evaluate` |
| 08 Recommendation/Feedback | 8600 | `POST /v1/recommendation/build` |

## Tests

Run `python -m pytest -q` from each Python module. Run `npm run build` and `npm audit` from `01_web_app`. Current test counts and the known Module 05 freshness failure are recorded in the root [README.md](README.md).
