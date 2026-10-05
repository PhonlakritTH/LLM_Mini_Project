# Modules 01–02: Web and API Quick Reference

The website requires Modules 01–08. Module 02 calls the agent and orchestrates integration, compatibility, decision, and final formatting. A downstream failure returns a degraded response; it will not fall back to a sample build.

For the complete local setup, provider configuration, and Docker instructions, see [README_RUN.md](README_RUN.md). For module-specific implementation status and next steps, see [Module 01](01_web_app/README.md) and [Module 02](02_api_backend/README.md).

## Ports

- Module 01 web app: `http://localhost:3000`
- Module 02 API: `http://localhost:8000`
- API docs during development: `http://localhost:8000/docs`

## Quick checks

From `01_web_app`, run `npm ci`, `npm run build`, and `npm audit`.

From `02_api_backend`, run `python -m pip install -r requirements.txt` and `python -m pytest -q`.
