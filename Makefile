.PHONY: install seed demo dev api web test lint

install:
	pip install -r requirements.txt
	cd frontend && npm install

seed:
	python -m backend.db.seed

demo:
	python -m backend.agent.orchestrator --demo

api:
	uvicorn backend.app:app --reload --port 8000

web:
	cd frontend && npm run dev

dev:
	@echo "Run 'make api' and 'make web' in two terminals (or use a process manager)."

test:
	pytest -q

lint:
	ruff check backend
