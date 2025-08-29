.PHONY: help install install-dev test clean lint format check-format docker-build docker-run run-api run-interactive health-check setup-env

help: ## Show this help message
	@echo "API Agent Framework - Available Commands"
	@echo "========================================"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	poetry install --only=main --no-dev

install-dev: ## Install development dependencies
	poetry install

test: ## Run tests
	poetry run pytest tests/ -v

clean: ## Clean up generated files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type f -name "*.log" -delete
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .coverage
	poetry env remove --all || true

lint: ## Run linting
	poetry run flake8 .
	poetry run mypy .

format: ## Format code
	poetry run black .
	poetry run isort .

check-format: ## Check if code is formatted correctly
	poetry run black --check .
	poetry run isort --check-only .

docker-build: ## Build Docker image
	docker build -t api-agent-framework .

docker-run: ## Run Docker container
	docker run -p 8080:8080 api-agent-framework

run-api: ## Run the API server
	poetry run uvicorn api.main:app --host 0.0.0.0 --port 8080 --reload

run-interactive: ## Run interactive mode
	poetry run python -m api.main interactive

health-check: ## Check system health
	curl -f http://localhost:8080/health || echo "Health check failed"

setup-env: ## Set up environment
	cp env.example .env
	@echo "Please edit .env file with your configuration"

poetry-lock: ## Update Poetry lock file
	poetry lock --no-update

poetry-update: ## Update all dependencies
	poetry update

poetry-add: ## Add a new dependency (usage: make poetry-add DEP=package_name)
	poetry add $(DEP)

poetry-add-dev: ## Add a new development dependency (usage: make poetry-add-dev DEP=package_name)
	poetry add --group dev $(DEP)
