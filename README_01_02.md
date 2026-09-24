# Run (modules 01 + 02)
Backend: cd 02_api_backend && pip install -r requirements.txt && cp .env.example .env && uvicorn app.main:app --reload   (tests: pytest)
Web app: cd 01_web_app && npm install && cp .env.example .env.local && npm run dev  -> http://localhost:3000
