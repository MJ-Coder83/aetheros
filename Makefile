.PHONY: dev test lint run-api install format typecheck clean help

# Default target
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

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
