# Market Analyst A2A Agent
# Multi-stage build for smaller image
#
# Build Context: This Dockerfile expects to be built from src/agent-market-analyst
# Example: docker build -f standalone/a2a/maf/Dockerfile .

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

# Copy dependency files from standalone/a2a/maf/
COPY standalone/a2a/maf/pyproject.toml standalone/a2a/maf/uv.lock ./

# Install dependencies (no BuildKit cache for ACR Tasks compatibility)
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

# Copy application code from standalone/a2a/maf/
COPY standalone/a2a/maf/__init__.py ./
COPY standalone/a2a/maf/agent.py ./
COPY standalone/a2a/maf/a2a_server.py ./
COPY standalone/a2a/maf/config.py ./
COPY standalone/a2a/maf/main.py ./

# Copy prompts from parent directory (relative to build context)
COPY prompts/ ./prompts/

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PROMPTS_DIR_OVERRIDE=/app/prompts

# Switch to non-root user
USER appuser

# Expose A2A server port
EXPOSE 8020

# Health check - A2A agent card endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8020/.well-known/agent-card.json')" || exit 1

# Run the A2A server
CMD ["python", "main.py"]
