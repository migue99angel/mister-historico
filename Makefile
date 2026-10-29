# Míster Histórico monorepo commands. Run `make help` to list targets.
.DEFAULT_GOAL := help
.PHONY: help test test-backend test-frontend lint lint-backend lint-frontend dev validate-content calibrate status usage usage-test clean-branches

REPO := migue99angel/mister-historico

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

lint-frontend: ## eslint, tsc and dependency-cruiser, plus ruff and mypy on the real-API E2E launcher
	cd frontend && npm run lint
	cd backend && uv run ruff check ../frontend/e2e/support && uv run ruff format --check ../frontend/e2e/support && uv run mypy --strict ../frontend/e2e/support

dev: ## Start the development environment (Docker Compose)
	docker compose up --build

validate-content: ## Validate historical content under content/
	cd backend && uv run mister content validate --root ../content

calibrate: ## Run engine calibration (pending: T2.7). Usage: make calibrate SEASON=<slug>
	@echo "Not implemented yet (T2.7)" && exit 1

status: ## Open tasks on the Project board, or one issue with N=<number> (status, blockers, PRs, latest comments)
ifdef N
	@gh issue view $(N) -R $(REPO) --json number,title,state,projectItems --jq '"#\(.number) \(.title) · \(.state) · \(.projectItems[0].status.name // "not in Project")"'
	@echo "Blocked by:"
	@gh api repos/$(REPO)/issues/$(N)/dependencies/blocked_by --jq '.[]|"  #\(.number) \(.state) \(.title)"'
	@echo "Pull requests:"
	@gh api graphql -F n=$(N) -f query='query($$n:Int!){repository(owner:"migue99angel",name:"mister-historico"){issue(number:$$n){timelineItems(itemTypes:[CROSS_REFERENCED_EVENT],last:20){nodes{...on CrossReferencedEvent{source{...on PullRequest{number state headRefName}}}}}}}}' \
		--jq '[.data.repository.issue.timelineItems.nodes[].source|select(.number)|"  #\(.number) \(.state) \(.headRefName)"]|unique[]'
	@echo "Latest comments:"
	@gh issue view $(N) -R $(REPO) --json comments --jq '.comments[-3:][]|"  [\(.createdAt[0:16])] \(.body|gsub("\\s+";" ")|.[0:400])"'
else
	@gh project item-list 1 --owner migue99angel --limit 500 --query "-status:Done" --format json --jq '.items[]|"\(.status)\t\(.priority)\t#\(.content.number)\t\(.title)"' | sort -t'	' -k1,1 -k2,2 -k3.2n
endif

usage: ## Local audit of Claude Code and Codex usage (writes outside the repo; see docs/agent-usage.md)
	python3 tools/agent_usage/agent_usage.py collect

usage-test: ## Tests of the usage audit tool
	python3 -m unittest discover -s tools/agent_usage -p 'test_*.py'

clean-branches: ## Remove local branches and worktrees of merged PRs (dry run; APPLY=1 to remove)
	tools/clean_branches.sh $(if $(APPLY),--apply)
