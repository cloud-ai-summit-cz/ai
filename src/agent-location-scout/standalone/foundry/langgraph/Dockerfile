FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
RUN pip install --no-cache-dir uv

# Copy dependency files first (for better layer caching)
COPY requirements.txt ./

# Install dependencies using uv (--prerelease=allow needed for azure-ai-agentserver-* packages)
RUN uv pip install --system --prerelease=allow -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash agent
USER agent

# Expose the hosting adapter port (azure-ai-agentserver-langgraph default is 8010)
EXPOSE 8010

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8010/health || exit 1

# Run the agent
CMD ["python", "main.py"]
