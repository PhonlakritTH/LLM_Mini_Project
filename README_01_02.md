# Modules 01–02: Web and API Quick Reference

Module 01 is the browser UI; Module 02 is its API gateway and orchestrator. The website request continues through Modules 03–08. Starting only these two modules shows the UI but cannot produce recommendations unless the downstream services are also running.

## Local ports

- Module 01 web app: `http://localhost:3000`
- Module 02 API: `http://localhost:8000`
- Interactive API docs: `http://localhost:8000/docs`

## Request path

`01 Web -> 02 API -> 03 Agent -> 04 External Data -> 02 -> 05 Snapshot -> 06 Compatibility -> 07 Decision -> 08 Formatter -> 01`

Current real-data limits: Module 04 can search Google Shopping prices through SerpApi; stock/spec/benchmark connectors are unavailable. Module 03 selects from a fixed candidate list, so live search results do not yet make its candidate catalog verified. Missing provider data remains unknown and marks the response degraded; a degraded result is not a verified purchase list. Read the individual [Module 01](01_web_app/README.md) and [Module 02](02_api_backend/README.md) docs and root [README](README.md) for complete status.

## Run

Use the all-service instructions in [README_RUN.md](README_RUN.md). In short, start all Python services with their configured URLs/internal token, then run:

```powershell
Set-Location 01_web_app
npm ci
npm run dev
```

Production build/type check:

```powershell
npm run build
```

Python backend tests:

```powershell
Set-Location 02_api_backend
python -m pip install -r requirements.txt
python -m pytest -q
```
