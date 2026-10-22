# Míster Histórico: comandos del monorepo. `make help` lista los objetivos.
.DEFAULT_GOAL := help
.PHONY: help test test-backend test-frontend lint lint-backend lint-frontend dev validate-content calibrate

help: ## Muestra esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

test: test-backend test-frontend ## Ejecuta todos los tests

test-backend: ## Tests del backend
	cd backend && uv run pytest

test-frontend: ## Tests del frontend
	cd frontend && npm run test

lint: lint-backend lint-frontend ## Lint, tipos y reglas de capas

lint-backend: ## ruff, mypy e import-linter
	cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run lint-imports

lint-frontend: ## eslint, tsc y dependency-cruiser
	cd frontend && npm run lint

dev: ## Levanta el entorno de desarrollo (Docker Compose)
	docker compose up --build

validate-content: ## Valida el contenido histórico (pendiente: T2.20)
	@echo "Pendiente de implementar en T2.20" && exit 1

calibrate: ## Ejecuta la calibración del motor (pendiente: T2.7). Uso: make calibrate SEASON=<slug>
	@echo "Pendiente de implementar en T2.7" && exit 1
