# Research Orchestrator API
# Multi-stage build for smaller image
#
# Build Context: This Dockerfile is built from src/agent-research-orchestrator
# Example: docker build -t agent-research-orchestrator .

# ============================================================
# Build stage - install dependencies
# ============================================================
FROM python:3.11-slim AS builder

# Install uv for fast dependency installation
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set uv environment variables
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies (using lock file for reproducible builds)
RUN uv sync --frozen --no-dev --no-install-project

# ============================================================
# Runtime stage - minimal image
# ============================================================
FROM python:3.11-slim AS runtime

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY __init__.py ./
COPY api.py ./
COPY config.py ./
COPY main.py ./
COPY models.py ./
COPY orchestrator.py ./
COPY retry_middleware.py ./
COPY telemetry.py ./
COPY trace_poller.py ./

# Copy prompts directory
COPY prompts/ ./prompts/

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Switch to non-root user
USER appuser

# Expose API port
EXPOSE 8000

# Health check - FastAPI docs endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the API server
CMD ["python", "main.py"]
