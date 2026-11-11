.PHONY: dev test eval seed demo lint schema
dev:
	docker compose up --build
test:
	python -m pytest -q
eval:
	python -m evals.runners.run_demo_eval --gate
seed:
	python -m gigsim.seed
demo:
	python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000
lint:
	python -m ruff check agent apps/api gigsim mcp_servers rag worker evals tests
schema:
	python -m apps.api.schemas.export
	npm --prefix apps/web run generate
