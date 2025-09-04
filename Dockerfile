# APISage - AI-Powered OpenAPI Analysis Tool
# Production-ready container

FROM python:3.13-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create user
RUN groupadd -r apisage && useradd -r -g apisage apisage

# Set work directory
WORKDIR /app

# Copy requirements and install dependencies
COPY pyproject.toml poetry.lock ./
RUN pip install poetry==1.8.3 && \
    poetry export -f requirements.txt --output requirements.txt --without-hashes && \
    pip install -r requirements.txt && \
    rm requirements.txt

# Copy application code
COPY --chown=apisage:apisage . .

# Create logs directory
RUN mkdir -p /app/logs && chown -R apisage:apisage /app/logs

# Switch to non-root user
USER apisage

# Expose ports
EXPOSE 8080 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Default command (can be overridden)
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]