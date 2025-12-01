"""FastAPI REST API for Research Orchestrator.

Exposes REST endpoints and SSE streaming for the research workflow.
"""

import asyncio
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

# SSE heartbeat interval in seconds (keeps connection alive during long operations)
SSE_HEARTBEAT_INTERVAL = 15

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


@app.get("/research/sessions/{session_id}/start", tags=["Research"])
async def start_session(session_id: str, request: Request) -> EventSourceResponse:
    """Start executing a research session with SSE progress streaming.

    This endpoint initiates the research workflow and streams progress
    events using Server-Sent Events (SSE). Uses GET because EventSource
    API only supports GET requests.

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
        """Generate SSE events from workflow execution with heartbeat keep-alive.
        
        Sends heartbeat events every SSE_HEARTBEAT_INTERVAL seconds to prevent
        connection timeouts during long-running agent operations.
        
        Uses async tasks instead of asyncio.wait_for to avoid cancelling the
        workflow generator mid-execution, which can leave it in an inconsistent state.
        """
        import json
        from datetime import datetime, timezone
        
        workflow_gen = orchestrator.run_research_workflow(session_id)
        workflow_exhausted = False
        pending_event_task: asyncio.Task | None = None
        
        try:
            while not workflow_exhausted:
                # Check if client disconnected
                if await request.is_disconnected():
                    logger.warning(f"Client disconnected from session {session_id}")
                    break
                
                # Create task for next event if not already pending
                if pending_event_task is None:
                    pending_event_task = asyncio.create_task(workflow_gen.__anext__())
                
                # Wait for either the event or heartbeat timeout
                done, _ = await asyncio.wait(
                    {pending_event_task},
                    timeout=SSE_HEARTBEAT_INTERVAL,
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                if pending_event_task in done:
                    # Event is ready
                    try:
                        event = pending_event_task.result()
                        yield {
                            "event": event.event_type.value,
                            "data": event.model_dump_json(),
                        }
                        pending_event_task = None  # Clear for next iteration
                    except StopAsyncIteration:
                        workflow_exhausted = True
                        pending_event_task = None
                else:
                    # Timeout - send heartbeat but DON'T cancel the pending task
                    heartbeat_data = json.dumps({
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "session_id": session_id,
                    })
                    yield {
                        "event": "heartbeat",
                        "data": heartbeat_data,
                    }
                    # Keep pending_event_task - it's still running
                    
        except RuntimeError as e:
            # Handle cross-task cancel scope errors from MCP cleanup
            if "cancel scope" in str(e):
                logger.debug(f"Ignoring cross-task cancel scope during SSE generator: {e}")
            else:
                logger.exception(f"RuntimeError in workflow for session {session_id}")
                yield {
                    "event": "error",
                    "data": f'{{"error": "{str(e)}"}}',
                }
        except Exception as e:
            logger.exception(f"Error in workflow for session {session_id}")
            yield {
                "event": "error",
                "data": f'{{"error": "{str(e)}"}}',
            }
        finally:
            # Cancel any pending task
            if pending_event_task and not pending_event_task.done():
                pending_event_task.cancel()
                try:
                    await pending_event_task
                except (asyncio.CancelledError, StopAsyncIteration):
                    pass
            
            # Explicitly close the workflow generator
            try:
                await workflow_gen.aclose()
            except RuntimeError as e:
                if "cancel scope" in str(e):
                    logger.debug(f"Ignoring cross-task cancel scope during generator close: {e}")
                else:
                    logger.debug(f"Error closing workflow generator: {e}")
            except Exception as e:
                logger.debug(f"Error closing workflow generator: {e}")

    return EventSourceResponse(event_generator())


# === Scratchpad Proxy Endpoints ===


@app.get("/research/sessions/{session_id}/scratchpad/plan", tags=["Research", "Scratchpad"])
async def get_plan(session_id: str) -> dict[str, Any]:
    """Get current research plan with all tasks.
    
    Returns the current plan with all tasks, their statuses, assignments, and priorities.
    Frontend should poll this endpoint after each SSE event to get the current state.
    This proxies to the MCP scratchpad read_plan tool.
    
    SECURITY: Uses session-scoped MCP tool with X-Session-ID header for isolation.

    Args:
        session_id: The session ID.

    Returns:
        Plan with tasks array and metadata.

    Raises:
        HTTPException: If session not found or scratchpad unavailable.
    """
    orchestrator = get_orchestrator()
    session = orchestrator.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    try:
        # Pass actual session_id for isolation
        plan_data = await orchestrator.get_scratchpad_plan(session_id=session_id)
        return {
            "session_id": session_id,
            **plan_data,
        }
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/research/sessions/{session_id}/scratchpad/notes", tags=["Research", "Scratchpad"])
async def get_notes(session_id: str) -> dict[str, Any]:
    """Get all research notes.
    
    Returns all notes collected during research, organized by author.
    Frontend should poll this endpoint after each SSE event to get current state.
    This proxies to the MCP scratchpad read_notes tool.
    
    SECURITY: Uses session-scoped MCP tool with X-Session-ID header for isolation.

    Args:
        session_id: The session ID.

    Returns:
        Notes array with metadata.

    Raises:
        HTTPException: If session not found or scratchpad unavailable.
    """
    orchestrator = get_orchestrator()
    session = orchestrator.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    try:
        # Pass actual session_id for isolation
        notes_data = await orchestrator.get_scratchpad_notes(session_id=session_id)
        return {
            "session_id": session_id,
            **notes_data,
        }
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/research/sessions/{session_id}/scratchpad/draft", tags=["Research", "Scratchpad"])
async def get_draft(session_id: str) -> dict[str, Any]:
    """Get current draft report sections.
    
    Returns all draft sections written so far.
    Frontend should poll this endpoint after each SSE event to get current state.
    This proxies to the MCP scratchpad read_draft tool.
    
    SECURITY: Uses session-scoped MCP tool with X-Session-ID header for isolation.

    Args:
        session_id: The session ID.

    Returns:
        Draft sections array with metadata.

    Raises:
        HTTPException: If session not found or scratchpad unavailable.
    """
    orchestrator = get_orchestrator()
    session = orchestrator.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    try:
        # Pass actual session_id for isolation
        draft_data = await orchestrator.get_scratchpad_draft(session_id=session_id)
        return {
            "session_id": session_id,
            **draft_data,
        }
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


# === Error Handlers ===


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler."""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)},
    )
