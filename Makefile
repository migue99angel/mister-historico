# Míster Histórico monorepo commands. Run `make help` to list targets.
.DEFAULT_GOAL := help
.PHONY: help test test-backend test-frontend lint lint-backend lint-frontend dev validate-content calibrate

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

test: test-backend test-frontend ## Run all tests

test-backend: ## Backend tests
	cd backend && uv run pytest

test-frontend: ## Frontend tests
	cd frontend && npm run test

lint: lint-backend lint-frontend ## Lint, type checks and layer rules

lint-backend: ## ruff, mypy and import-linter
	cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run lint-imports

lint-frontend: ## eslint, tsc and dependency-cruiser
	cd frontend && npm run lint

dev: ## Start the development environment (Docker Compose)
	docker compose up --build

validate-content: ## Validate historical content (pending: T2.20)
	@echo "Not implemented yet (T2.20)" && exit 1

calibrate: ## Run engine calibration (pending: T2.7). Usage: make calibrate SEASON=<slug>
	@echo "Not implemented yet (T2.7)" && exit 1
