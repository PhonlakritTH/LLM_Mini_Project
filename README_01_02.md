# Modules 01–02: Web and API Quick Reference

The website requires the full active path: Module 01 calls Module 02, which calls Module 03, which queries Module 04. Starting only Modules 01–02 will result in a clear `503` while the agent is unavailable; it will not use sample recommendation data.

For the complete local setup, provider configuration, and Docker instructions, see [README_RUN.md](README_RUN.md). For module-specific implementation status and next steps, see [Module 01](01_web_app/README.md) and [Module 02](02_api_backend/README.md).

## Ports

- Module 01 web app: `http://localhost:3000`
- Module 02 API: `http://localhost:8000`
- API docs during development: `http://localhost:8000/docs`

## Quick checks

From `01_web_app`, run `npm ci`, `npm run build`, and `npm audit`.

From `02_api_backend`, run `python -m pip install -r requirements.txt` and `python -m pytest -q`.
