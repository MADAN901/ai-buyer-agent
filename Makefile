.PHONY: setup seed run test eval demo docker-up docker-down clean

PYTHON ?= python3
VENV := backend/.venv
PIP := $(VENV)/bin/pip
PY := $(VENV)/bin/python
UVICORN := $(VENV)/bin/uvicorn

setup: $(VENV)/bin/activate frontend/node_modules
	@echo "Setup complete. Copy .env.example to .env if you have not already."

$(VENV)/bin/activate: backend/requirements.txt
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r backend/requirements.txt
	touch $(VENV)/bin/activate

frontend/node_modules: frontend/package.json
	cd frontend && npm install

seed:
	@test -f .env || cp .env.example .env
	mkdir -p data
	cd backend && ../$(PY) -m app.seed

run:
	@test -f .env || cp .env.example .env
	mkdir -p data
	@echo "Starting backend on :8000 and frontend on :5173..."
	$(MAKE) -j2 run-backend run-frontend

run-backend:
	cd backend && ../$(PY) -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run-frontend:
	cd frontend && npm run dev -- --host 0.0.0.0

test:
	cd backend && ../$(PY) -m pytest tests/ -v

eval:
	PYTHONPATH=backend:. $(PY) -m evals.run

demo:
	@echo "Demo: ensure LLM_PROVIDER=mock in .env, then open http://localhost:5173/scenarios"
	$(MAKE) seed run

docker-up:
	docker compose up --build

docker-down:
	docker compose down

clean:
	rm -rf $(VENV) frontend/node_modules frontend/dist data/*.db
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
