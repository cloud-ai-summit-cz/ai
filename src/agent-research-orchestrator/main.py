"""Main entry point for Research Orchestrator.

Runs the FastAPI server using uvicorn.
"""

import logging
import sys

import uvicorn

# Configure telemetry FIRST before any other imports that might create spans
from telemetry import configure_telemetry
configure_telemetry()

from config import get_settings


def _configure_logging() -> logging.Logger:
    """Configure application and Azure SDK logging.

    - App logs default to INFO.
    - Azure SDK/identity/client logs are raised to WARNING to reduce noise.
    """

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Quiet down Azure SDKs to WARNING by default
    for name in [
        "azure",
        "azure.core",
        "azure.identity",
        "azure.ai",
        "azure.monitor",
    ]:
        logging.getLogger(name).setLevel(logging.WARNING)

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
