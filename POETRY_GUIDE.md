# Poetry Dependency Management Guide

## 🎯 Why Poetry Instead of pip?

**Poetry** provides several advantages over traditional `pip` + `requirements.txt`:

### ✅ **Benefits**
- **Faster Installation**: Parallel dependency resolution and downloads
- **Better Dependency Resolution**: Automatic conflict detection and resolution
- **Lock File**: Reproducible builds with `poetry.lock`
- **Virtual Environment Management**: Automatic venv creation and management
- **Modern Python Packaging**: PEP 517/518 compliant
- **Dependency Groups**: Separate dev, production, and optional dependencies

### 🚫 **What We Removed**
- `requirements.txt` - No longer needed
- Manual dependency version conflicts
- Inconsistent environment issues

## 🚀 Getting Started

### 1. Install Poetry

```bash
# macOS/Linux
curl -sSL https://install.python-poetry.org | python3 -

# Windows (PowerShell)
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -

# Add to PATH (macOS/Linux)
export PATH="$HOME/.local/bin:$PATH"
```

### 2. Verify Installation

```bash
poetry --version
# Poetry (version 2.1.4)
```

## 📦 Project Commands

### **Install Dependencies**

```bash
# Install all dependencies (including dev)
poetry install

# Install only production dependencies
poetry install --only=main

# Install specific group
poetry install --only=dev
poetry install --only=production
```

### **Add New Dependencies**

```bash
# Add production dependency
poetry add fastapi

# Add development dependency
poetry add --group dev pytest

# Add with specific version
poetry add "fastapi>=0.110.0"

# Add with extras
poetry add "uvicorn[standard]"
```

### **Remove Dependencies**

```bash
# Remove dependency
poetry remove fastapi

# Remove from specific group
poetry remove --group dev pytest
```

### **Update Dependencies**

```bash
# Update all dependencies
poetry update

# Update specific dependency
poetry update fastapi

# Update lock file without changing versions
poetry lock --no-update
```

### **Show Dependencies**

```bash
# Show dependency tree
poetry show --tree

# Show specific dependency info
poetry show fastapi

# Show outdated packages
poetry show --outdated
```

## 🐳 Docker Integration

### **Dockerfile with Poetry**

```dockerfile
# Install Poetry
RUN python3 -m venv $POETRY_VENV \
    && $POETRY_VENV/bin/pip install -U pip setuptools \
    && $POETRY_VENV/bin/pip install "poetry==$POETRY_VERSION"

# Configure Poetry
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --only=main --no-dev --no-interaction --no-ansi
```

### **Benefits in Docker**
- **Faster Builds**: Poetry's dependency resolution is more efficient
- **Smaller Images**: Better dependency pruning
- **Reproducible**: Lock file ensures consistent builds
- **Cleaner**: No virtual environment overhead in containers

## 🔧 Development Workflow

### **Local Development**

```bash
# 1. Clone repository
git clone <repo-url>
cd api-agent-framework

# 2. Install Poetry (if not installed)
curl -sSL https://install.python-poetry.org | python3 -

# 3. Install dependencies
poetry install

# 4. Activate virtual environment
poetry shell

# 5. Run commands
poetry run python -m api.main
poetry run pytest
poetry run black .
```

### **Makefile Integration**

```makefile
install: ## Install production dependencies
	poetry install --only=main --no-dev

install-dev: ## Install development dependencies
	poetry install

test: ## Run tests
	poetry run pytest tests/ -v

lint: ## Run linting
	poetry run flake8 .
	poetry run mypy .

format: ## Format code
	poetry run black .
	poetry run isort .
```

## 📁 Project Structure

```
api-agent-framework/
├── pyproject.toml          # Poetry configuration
├── poetry.lock            # Locked dependency versions
├── api/                   # Application code
├── agents/                # AI agents
├── core/                  # Core functionality
├── config/                # Configuration
├── infrastructure/        # Backend services
├── sdk/                   # SDK components
└── utils/                 # Utilities
```

## ⚙️ Configuration

### **pyproject.toml Structure**

```toml
[tool.poetry]
name = "api-agent-framework"
version = "1.0.0"
description = "Self-Hosted AI Agent Framework"
authors = ["API Agent Team <team@api-agent.dev>"]

[tool.poetry.dependencies]
python = "^3.9"
fastapi = "^0.110.0"
uvicorn = {extras = ["standard"], version = "^0.27.0"}

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
black = "^23.12.0"

[tool.poetry.group.production.dependencies]
gunicorn = "^21.0.0"
```

### **Dependency Version Constraints**

```toml
# Exact version
fastapi = "0.110.0"

# Compatible release (^)
fastapi = "^0.110.0"  # >=0.110.0, <1.0.0

# Compatible release (~)
fastapi = "~0.110.0"  # >=0.110.0, <0.111.0

# Greater than
fastapi = ">=0.110.0"

# Range
fastapi = ">=0.110.0,<0.120.0"
```

## 🚨 Troubleshooting

### **Common Issues**

#### **1. Poetry Command Not Found**
```bash
# Add to PATH
export PATH="$HOME/.local/bin:$PATH"

# Or use full path
~/.local/bin/poetry --version
```

#### **2. Dependency Conflicts**
```bash
# Check conflicts
poetry show --tree

# Update lock file
poetry lock --no-update

# Force update
poetry update
```

#### **3. Virtual Environment Issues**
```bash
# Remove all environments
poetry env remove --all

# Create new environment
poetry install
```

#### **4. Docker Build Failures**
```bash
# Clear Docker cache
docker system prune -a

# Rebuild without cache
docker build --no-cache -t api-agent-framework .
```

## 📚 Additional Resources

- **Official Documentation**: https://python-poetry.org/docs/
- **GitHub Repository**: https://github.com/python-poetry/poetry
- **Community**: https://python-poetry.org/community/

## 🎉 Migration Complete!

Your project now uses **Poetry** for modern, fast, and reliable dependency management!

**Key Benefits:**
- ✅ **Faster builds** in Docker
- ✅ **Better dependency resolution**
- ✅ **Reproducible environments**
- ✅ **Cleaner project structure**
- ✅ **Modern Python packaging standards**
