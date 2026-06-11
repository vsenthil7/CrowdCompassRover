# CrowdCompass Rover — developer entry points
.PHONY: help install backend-install frontend-install seed \
        run-backend run-frontend run-mcp test test-backend test-frontend test-e2e \
        cov lint clean

help:
	@echo "CrowdCompass Rover make targets:"
	@echo "  install           Install backend + frontend deps"
	@echo "  seed              Generate / load fixture city-event data"
	@echo "  run-mcp           Start local mock Elastic MCP server"
	@echo "  run-backend       Start FastAPI backend"
	@echo "  run-frontend      Start Vite dev server"
	@echo "  test              Run all tests (backend + frontend + e2e)"
	@echo "  test-backend      pytest with 100% coverage gate"
	@echo "  test-frontend     vitest with 100% coverage gate"
	@echo "  test-e2e          Playwright end-to-end suite"
	@echo "  test-real         Re-run backend suite in APP_MODE=real (needs creds)"
	@echo "  cov               Print coverage summaries"

install: backend-install frontend-install

backend-install:
	cd backend && pip install -e ".[dev]" --break-system-packages

frontend-install:
	cd frontend && npm install
	cd e2e && npm install

seed:
	cd backend && python -m app.data.seed

run-mcp:
	cd backend && python -m app.mcp.mock_server

run-backend:
	cd backend && uvicorn app.main:app --reload --port 8000

run-frontend:
	cd frontend && npm run dev

test: test-backend test-frontend test-e2e

test-backend:
	cd backend && pytest

test-frontend:
	cd frontend && npm run test:cov

test-e2e:
	cd e2e && npm run test

test-real:
	cd backend && APP_MODE=real pytest

cov:
	cd backend && coverage report
	cd frontend && npm run coverage:report || true

clean:
	rm -rf backend/.pytest_cache backend/htmlcov backend/.coverage \
	       frontend/coverage frontend/dist e2e/playwright-report e2e/test-results
