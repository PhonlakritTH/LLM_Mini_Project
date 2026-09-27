up:
	docker compose up -d
down:
	docker compose down
logs:
	docker compose logs -f
rebuild:
	docker compose up -d --build
test:
	for d in 02_api_backend 03_pc_build_ai_agent 04_external_data_services 05_data_integration 06_compatibility_knowledge_services 07_decision_llm_engine 08_recommendation_feedback; do \
		echo "== $$d =="; (cd $$d && cp -n .env.example .env 2>/dev/null; python -m pytest -q); \
	done
