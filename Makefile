# APISage - AI-Powered OpenAPI Analysis Tool
# Makefile for easy setup, development, and deployment

.PHONY: help install dev build run stop clean test lint format docker-build docker-run docker-stop docker-clean

# Default target
help: ## Show this help message
	@echo "APISage - AI-Powered OpenAPI Analysis Tool"
	@echo "=========================================="
	@echo ""
	@echo "Available commands:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Development setup
install: ## Install dependencies using Poetry
	@echo "📦 Installing dependencies..."
	poetry install
	@echo "✅ Dependencies installed successfully!"

dev: ## Start development environment (API + Gradio)
	@echo "🚀 Starting development environment..."
	@echo "📡 API will be available at: http://localhost:8080"
	@echo "🌐 Gradio UI will be available at: http://localhost:7860"
	@echo "📚 API docs at: http://localhost:8080/docs"
	@echo ""
	@echo "Press Ctrl+C to stop both services"
	@trap 'kill %1; kill %2' INT; \
	poetry run uvicorn api.main:app --host 0.0.0.0 --port 8080 --reload & \
	poetry run python gradio_app.py & \
	wait

api: ## Start only the API server
	@echo "📡 Starting API server at http://localhost:8080"
	@echo "📚 API docs at: http://localhost:8080/docs"
	poetry run uvicorn api.main:app --host 0.0.0.0 --port 8080 --reload

ui: ## Start only the Gradio UI
	@echo "🌐 Starting Gradio UI at http://localhost:7860"
	poetry run python gradio_app.py

# Production build and run
build: ## Build the application for production
	@echo "🔨 Building application..."
	@echo "✅ Application is ready for production deployment"
	@echo "💡 Use 'make docker-build' for Docker deployment"
	@echo "✅ Build completed!"

run: ## Run the application in production mode
	@echo "🚀 Starting APISage in production mode..."
	@echo "📡 API: http://localhost:8080"
	@echo "🌐 UI: http://localhost:7860"
	@trap 'kill %1; kill %2' INT; \
	poetry run uvicorn api.main:app --host 0.0.0.0 --port 8080 & \
	poetry run python gradio_app.py & \
	wait

# Docker commands
docker-check: ## Check if Docker is running
	@echo "🔍 Checking Docker daemon..."
	@if ! docker info >/dev/null 2>&1; then \
		echo "❌ Docker daemon is not running!"; \
		echo "💡 Please start Docker Desktop or Docker daemon"; \
		echo "   - macOS: Start Docker Desktop application"; \
		echo "   - Linux: sudo systemctl start docker"; \
		exit 1; \
	fi
	@echo "✅ Docker daemon is running"

docker-status: ## Check Docker container status
	@echo "📊 Docker Container Status"
	@echo "========================="
	@if docker ps -q -f name=apisage >/dev/null 2>&1; then \
		echo "✅ APISage container is running"; \
		docker ps -f name=apisage --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"; \
	else \
		echo "❌ APISage container is not running"; \
		echo "💡 Start it with: make docker-run"; \
	fi

docker-build: docker-check ## Build Docker image
	@echo "🐳 Building Docker image..."
	docker build -t apisage:latest .
	@echo "✅ Docker image built successfully!"

docker-run: docker-check ## Run APISage in Docker container
	@echo "🐳 Starting APISage in Docker..."
	@echo "📡 API: http://localhost:8080"
	@echo "🌐 UI: http://localhost:7860"
	@if [ -z "$$OPENAI_API_KEY" ]; then \
		echo "⚠️  Warning: OPENAI_API_KEY environment variable not set"; \
		echo "💡 Set it with: export OPENAI_API_KEY=your-key-here"; \
	fi
	docker run -d \
		--name apisage \
		-p 8080:8080 \
		-p 7860:7860 \
		-e OPENAI_API_KEY=$${OPENAI_API_KEY} \
		-v $$(pwd)/logs:/app/logs \
		apisage:latest
	@echo "✅ APISage started in Docker!"
	@echo "📋 Container name: apisage"
	@echo "🔍 View logs: make docker-logs"

docker-run-interactive: docker-check ## Run APISage in Docker container (interactive)
	@echo "🐳 Starting APISage in Docker (interactive mode)..."
	@if [ -z "$$OPENAI_API_KEY" ]; then \
		echo "⚠️  Warning: OPENAI_API_KEY environment variable not set"; \
		echo "💡 Set it with: export OPENAI_API_KEY=your-key-here"; \
	fi
	docker run -it --rm \
		--name apisage-interactive \
		-p 8080:8080 \
		-p 7860:7860 \
		-e OPENAI_API_KEY=$${OPENAI_API_KEY} \
		-v $$(pwd)/logs:/app/logs \
		apisage:latest

docker-stop: ## Stop Docker container
	@echo "🛑 Stopping APISage Docker container..."
	@if docker ps -q -f name=apisage >/dev/null 2>&1; then \
		docker stop apisage; \
		docker rm apisage; \
		echo "✅ Docker container stopped and removed!"; \
	else \
		echo "ℹ️  No running APISage container found"; \
	fi

docker-logs: ## View Docker container logs
	@echo "📋 Viewing APISage Docker logs..."
	@if docker ps -q -f name=apisage >/dev/null 2>&1; then \
		docker logs -f apisage; \
	else \
		echo "❌ APISage container is not running"; \
		echo "💡 Start it with: make docker-run"; \
		exit 1; \
	fi

docker-clean: ## Clean up Docker resources
	@echo "🧹 Cleaning up Docker resources..."
	@if docker ps -q -f name=apisage >/dev/null 2>&1; then \
		echo "🛑 Stopping running container..."; \
		docker stop apisage; \
		docker rm apisage; \
	fi
	@if docker images -q apisage:latest >/dev/null 2>&1; then \
		echo "🗑️  Removing Docker image..."; \
		docker rmi apisage:latest; \
	fi
	@echo "✅ Docker cleanup completed!"

# Development tools
test: ## Run tests
	@echo "🧪 Running tests..."
	poetry run pytest -v

lint: ## Run linting
	@echo "🔍 Running linting..."
	poetry run flake8 . --exclude=venv,__pycache__,.git
	poetry run mypy . --exclude=venv

format: ## Format code
	@echo "✨ Formatting code..."
	poetry run black .
	poetry run isort .

# Utility commands
clean: ## Clean up temporary files
	@echo "🧹 Cleaning up temporary files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/
	rm -rf .pytest_cache/
	@echo "✅ Cleanup completed!"

logs: ## View application logs
	@echo "📋 Viewing application logs..."
	@if [ -f logs/apisage_gradio_*.log ]; then \
		echo "=== Gradio Logs ==="; \
		tail -f logs/apisage_gradio_*.log; \
	else \
		echo "No logs found. Start the application first."; \
	fi

status: ## Check application status
	@echo "📊 APISage Status Check"
	@echo "======================"
	@echo ""
	@echo "🔍 Checking API health..."
	@curl -s http://localhost:8080/health > /dev/null && echo "✅ API is running" || echo "❌ API is not running"
	@echo ""
	@echo "🔍 Checking Gradio UI..."
	@curl -s http://localhost:7860 > /dev/null && echo "✅ Gradio UI is running" || echo "❌ Gradio UI is not running"
	@echo ""
	@echo "🐳 Docker container status:"
	@docker ps --filter "name=apisage" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" || echo "No Docker containers running"

# Environment setup
setup-env: ## Create environment file from template
	@echo "⚙️  Setting up environment..."
	@if [ ! -f .env ]; then \
		cp env.example .env; \
		echo "✅ Created .env file from template"; \
		echo "📝 Please edit .env file with your configuration"; \
	else \
		echo "⚠️  .env file already exists"; \
	fi

# Quick start
quick-start: setup-env install ## Quick start setup (env + install)
	@echo "🚀 Quick start completed!"
	@echo ""
	@echo "Next steps:"
	@echo "1. Edit .env file with your OpenAI API key"
	@echo "2. Run 'make dev' to start development environment"
	@echo "3. Or run 'make docker-build && make docker-run' for Docker deployment"

# Production deployment
deploy: docker-build docker-run ## Deploy to production (Docker)
	@echo "🚀 Production deployment completed!"
	@echo "📡 API: http://localhost:8080"
	@echo "🌐 UI: http://localhost:7860"
	@echo "🔍 View logs: make docker-logs"
