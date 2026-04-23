.PHONY: dev test lint run-api install format typecheck clean help
.PHONY: worktree-add worktree-list worktree-remove worktree-clean

# Default target
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install Python dependencies
	uv sync

dev: ## Start the API dev server with hot reload
	uvicorn services.api.main:app --reload --host 0.0.0.0 --port 8000

run-api: ## Start the API server (production)
	uvicorn services.api.main:app --host 0.0.0.0 --port 8000 --workers 4

test: ## Run the test suite
	pytest tests/ -v --tb=short

lint: ## Run ruff linter
	ruff check . --fix

format: ## Run ruff formatter
	ruff format .

typecheck: ## Run mypy type checking
	mypy packages/ services/ --ignore-missing-imports

clean: ## Remove build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache

# ---------------------------------------------------------------------------
# Git Worktrees
# ---------------------------------------------------------------------------

worktree-add: ## Create a worktree — usage: make worktree-add WT=feat/my-feature
	@if [ -z "$(WT)" ]; then echo "Usage: make worktree-add WT=<branch-name>"; exit 1; fi
	@mkdir -p worktrees
	@git worktree add -b "$(WT)" "worktrees/$(WT)" 2>/dev/null || \
		git worktree add "worktrees/$(WT)" "$(WT)" 2>/dev/null || \
		echo "Error: Could not create worktree for '$(WT)'. It may already exist."
	@echo "✓ Worktree created: worktrees/$(WT)"

worktree-list: ## List all active git worktrees
	@git worktree list

worktree-remove: ## Remove a worktree — usage: make worktree-remove WT=feat/my-feature
	@if [ -z "$(WT)" ]; then echo "Usage: make worktree-remove WT=<branch-name>"; exit 1; fi
	@git worktree remove "worktrees/$(WT)" 2>/dev/null && \
		echo "✓ Worktree removed: worktrees/$(WT)" || \
		echo "Error: Worktree 'worktrees/$(WT)' not found or could not be removed."
	@git worktree prune

worktree-clean: ## Remove all worktrees (keeps main checkout only)
	@git worktree list --porcelain | grep "^worktree " | grep -v "^worktree $(CURDIR)$$" | \
		while read -r line; do \
			wt=$$(echo "$$line" | sed 's/^worktree //'); \
			echo "Removing $$wt"; \
			git worktree remove "$$wt" --force 2>/dev/null; \
		done
	@git worktree prune
	@echo "✓ All worktrees cleaned up"
