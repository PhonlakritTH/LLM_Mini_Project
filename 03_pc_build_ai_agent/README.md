# 03 PC Build AI Agent
Run: pip install -r requirements.txt && cp .env.example .env && uvicorn app.main:app --port 8100 --reload   (tests: pytest)
Call: POST /v1/agent/run with header X-Internal-Token (body = AgentRequest). Returns AgentResult with an evidence_package for module 07.
Graph: classify > extract > ask_missing > plan > fetch(price||stock||benchmark) > integrate > compatibility > alternatives_rag > quality > package
Empty *_SERVICE_URL uses built-in mocks. MOCK_FAIL=stock simulates an outage.
