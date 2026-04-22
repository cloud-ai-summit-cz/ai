"""Main entry point for Research Orchestrator.

Runs the FastAPI server using uvicorn.
"""

import logging
import re
import sys

import uvicorn

# Configure telemetry FIRST before any other imports that might create spans
from telemetry import configure_telemetry
configure_telemetry()

from config import get_settings


# Pattern for noisy polling endpoints we want to suppress at INFO level
# Matches scratchpad polling: /research/sessions/{uuid}/scratchpad/{plan|notes|draft}
SCRATCHPAD_POLL_PATTERN = re.compile(
    r'/research/sessions/[a-f0-9-]+/scratchpad/(plan|notes|draft)'
)


class SuppressScratchpadPollingFilter(logging.Filter):
    """Filter to suppress frequent scratchpad polling access logs.
    
    These endpoints are polled by the frontend every few seconds to get
    updated state. Logging every request clutters the output and makes
    it hard to see important events like MCP tool calls.
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Return False to suppress, True to allow the log record."""
        # Check if this is an access log with a scratchpad polling path
        message = record.getMessage()
        if SCRATCHPAD_POLL_PATTERN.search(message):
            # Suppress INFO level, but allow WARNING/ERROR through
            return record.levelno > logging.INFO
        return True


def _configure_logging() -> logging.Logger:
    """Configure application and Azure SDK logging.

    - App logs default to INFO.
    - Azure SDK/identity/client logs are raised to WARNING to reduce noise.
    - Uvicorn access logs for scratchpad polling endpoints are suppressed.
    """

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Quiet down Azure SDKs, HTTP clients, and framework internals to WARNING
    for name in [
        "azure",
        "azure.core",
        "azure.identity",
        "azure.ai",
        "azure.monitor",
        "httpx",
        "mcp.client.streamable_http",
        "agent_framework",
    ]:
        logging.getLogger(name).setLevel(logging.WARNING)
    
    # Add filter to suppress noisy scratchpad polling access logs
    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    uvicorn_access_logger.addFilter(SuppressScratchpadPollingFilter())

    return logging.getLogger(__name__)


logger = _configure_logging()


def main() -> None:
    """Run the FastAPI server."""
    settings = get_settings()

    logger.info("Starting Research Orchestrator API")
    logger.info(f"Host: {settings.api_host}")
    logger.info(f"Port: {settings.api_port}")
    logger.info(f"Reload: {settings.api_reload}")

    uvicorn.run(
        "api:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
