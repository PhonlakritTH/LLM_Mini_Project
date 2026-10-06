# Modules 01–02: Web App and API

Module 01 is the Thai PC-spec planning UI. Module 02 is the development API gateway and orchestrator. The request continues through Modules 03–08; run all services via [README_RUN.md](README_RUN.md).

## Local ports

- Web app: `http://localhost:3000`
- API: `http://localhost:8000`
- Interactive API docs: `http://localhost:8000/docs`

The form accepts budget, use case, CPU/GPU brand/model preferences and existing parts. Results show compatibility, sourced specs and market-reference price ranges. The app has no store/stock/checkout. A SerpApi key is required for live Google Shopping reference prices; missing prices remain unknown and prevent claiming a confirmed budget fit.

For the web app alone:

```powershell
Set-Location 01_web_app
npm ci
npm run dev
```

The API needs Modules 03–08. `/v1/auth/dev-token` is for local development only and is not production authentication.
