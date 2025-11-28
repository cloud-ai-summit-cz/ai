"""FastAPI REST API for Research Orchestrator.

Exposes REST endpoints and SSE streaming for the research workflow.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from __init__ import __version__
from config import get_settings
from models import (
    CreateSessionRequest,
    HealthStatus,
    ResearchSession,
    SessionListResponse,
)
from orchestrator import AgentOrchestrator

logger = logging.getLogger(__name__)

# Global orchestrator instance (initialized in lifespan)
_orchestrator: AgentOrchestrator | None = None


def get_orchestrator() -> AgentOrchestrator:
    """Get the global orchestrator instance."""
    if _orchestrator is None:
        raise RuntimeError("Orchestrator not initialized")
    return _orchestrator


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    global _orchestrator

    settings = get_settings()
    logger.info(f"Starting Research Orchestrator v{__version__}")
    logger.info(f"Foundry endpoint: {settings.azure_ai_foundry_endpoint}")

    # Initialize orchestrator
    _orchestrator = AgentOrchestrator(settings)
    await _orchestrator.__aenter__()

    yield

    # Cleanup
    if _orchestrator:
        await _orchestrator.__aexit__(None, None, None)
    logger.info("Research Orchestrator shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Research Orchestrator API",
    description="MAF-based orchestrator for multi-agent research workflows",
    version=__version__,
    lifespan=lifespan,
)

# CORS middleware for web UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === Health Endpoints ===


@app.get("/health", response_model=HealthStatus, tags=["Health"])
async def health_check() -> HealthStatus:
    """Check API health and Foundry connectivity."""
    orchestrator = get_orchestrator()
    health_data = await orchestrator.check_health()

    return HealthStatus(
        status="healthy",
        version=__version__,
        foundry_endpoint=health_data["foundry_endpoint"],
        model_deployment=health_data["model_deployment"],
    )


@app.get("/", tags=["Health"])
async def root() -> dict[str, str]:
    """Root endpoint with API info."""
    return {
        "service": "research-orchestrator",
        "version": __version__,
        "docs": "/docs",
    }


# === Session Endpoints ===


@app.post("/research/sessions", response_model=ResearchSession, tags=["Research"])
async def create_session(request: CreateSessionRequest) -> ResearchSession:
    """Create a new research session.

    Creates a pending session that can be started later. The session will
    coordinate market-analyst, competitor-analyst, and synthesizer agents.

    Args:
        request: The session creation request with query and optional context.

    Returns:
        The created session with its ID.
    """
    orchestrator = get_orchestrator()
    session = orchestrator.create_session(query=request.query, context=request.context)
    return session


@app.get("/research/sessions", response_model=SessionListResponse, tags=["Research"])
async def list_sessions() -> SessionListResponse:
    """List all research sessions."""
    orchestrator = get_orchestrator()
    sessions = orchestrator.list_sessions()
    return SessionListResponse(sessions=sessions, total=len(sessions))


@app.get("/research/sessions/{session_id}", response_model=ResearchSession, tags=["Research"])
async def get_session(session_id: str) -> ResearchSession:
    """Get a specific research session by ID.

    Args:
        session_id: The session ID to retrieve.

    Returns:
        The session if found.

    Raises:
        HTTPException: If session not found.
    """
    orchestrator = get_orchestrator()
    session = orchestrator.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return session


@app.post("/research/sessions/{session_id}/start", tags=["Research"])
async def start_session(session_id: str, request: Request) -> EventSourceResponse:
    """Start executing a research session with SSE progress streaming.

    This endpoint initiates the research workflow and streams progress
    events using Server-Sent Events (SSE). The workflow:
    1. Runs market-analyst and competitor-analyst concurrently
    2. Passes results to synthesizer for final recommendations

    Args:
        session_id: The session ID to start.
        request: The HTTP request (for client disconnect detection).

    Returns:
        SSE stream of workflow events.

    Raises:
        HTTPException: If session not found or already running.
    """
    orchestrator = get_orchestrator()
    session = orchestrator.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    if session.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Session {session_id} is already {session.status}",
        )

    async def event_generator() -> AsyncGenerator[dict[str, Any], None]:
        """Generate SSE events from workflow execution."""
        try:
            async for event in orchestrator.run_research_workflow(session_id):
                # Check if client disconnected
                if await request.is_disconnected():
                    logger.warning(f"Client disconnected from session {session_id}")
                    break

                yield {
                    "event": event.event_type.value,
                    "data": event.model_dump_json(),
                }
        except Exception as e:
            logger.exception(f"Error in workflow for session {session_id}")
            yield {
                "event": "error",
                "data": f'{{"error": "{str(e)}"}}',
            }

    return EventSourceResponse(event_generator())


# === Error Handlers ===


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler."""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)},
    )
