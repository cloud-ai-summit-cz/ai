"""FastAPI REST API for Research Orchestrator.

Exposes REST endpoints and SSE streaming for the research workflow.

ADR-007: UI events are generated directly by the orchestrator middleware,
providing real-time updates without the 2-5 second latency from App Insights polling.
OpenTelemetry traces still flow to App Insights for observability dashboards.
"""

import asyncio
import logging
import re
import sys
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator


# === Logging Configuration ===
# MUST be configured BEFORE importing other modules so their loggers work correctly

# Pattern for noisy polling endpoints we want to suppress at INFO level
SCRATCHPAD_POLL_PATTERN = re.compile(
    r'/research/sessions/[a-f0-9-]+/scratchpad/(plan|notes|draft)'
)


class SuppressScratchpadPollingFilter(logging.Filter):
    """Filter to suppress frequent scratchpad polling access logs."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Return False to suppress, True to allow the log record."""
        message = record.getMessage()
        if SCRATCHPAD_POLL_PATTERN.search(message):
            return record.levelno > logging.INFO
        return True


def _configure_logging() -> None:
    """Configure logging for the API worker process.
    
    This runs when api.py is imported by uvicorn, ensuring logging
    is properly configured in the worker process (not just the parent).
    """
    # Force reconfigure logging (override any existing config)
    root_logger = logging.getLogger()
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Configure with proper format and stdout handler
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,  # Override any existing configuration
    )
    
    # Quiet down Azure SDKs, HTTP clients, and framework internals
    for name in [
        "azure", "azure.core", "azure.identity", "azure.ai", "azure.monitor",
        "httpx", "mcp.client.streamable_http", "agent_framework",
    ]:
        logging.getLogger(name).setLevel(logging.WARNING)
    
    # Add filter to suppress scratchpad polling access logs
    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    # Avoid adding duplicate filters
    if not any(isinstance(f, SuppressScratchpadPollingFilter) for f in uvicorn_access_logger.filters):
        uvicorn_access_logger.addFilter(SuppressScratchpadPollingFilter())


# Configure logging FIRST - before any other imports
_configure_logging()


# Now import other modules (their loggers will inherit from root)
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from opentelemetry import trace
from sse_starlette.sse import EventSourceResponse

from __init__ import __version__
from config import get_settings
from models import (
    AnswersRequest,
    AnswersResponse,
    CreateSessionRequest,
    HealthStatus,
    QuestionsResponse,
    ResearchSession,
    SessionListResponse,
)
from orchestrator import AgentOrchestrator
from telemetry import get_tracer, set_session_context


logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)

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


@app.get("/health/detailed", tags=["Health"])
async def health_check_detailed() -> dict[str, Any]:
    """Detailed health check including observability status."""
    orchestrator = get_orchestrator()
    settings = get_settings()
    health_data = await orchestrator.check_health()

    return {
        "status": "healthy",
        "version": __version__,
        "foundry_endpoint": health_data["foundry_endpoint"],
        "model_deployment": health_data["model_deployment"],
        "mcp_scratchpad": health_data.get("mcp_scratchpad"),
        "observability": {
            "opentelemetry_enabled": True,
            "app_insights_configured": bool(settings.log_analytics_workspace_id),
            # Note: ADR-007 - trace polling is no longer used for UI events
            # Traces still flow to App Insights for observability dashboards
        },
    }


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
    
    with tracer.start_as_current_span("create_research_session") as span:
        session = orchestrator.create_session(query=request.query, context=request.context)
        set_session_context(span, session.session_id, request.query)
        span.set_attribute("session.status", session.status)
        logger.info(f"Created session {session.session_id} with query: {request.query[:100]}...")
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
    
    Creates a parent span for the entire research session that provides
    the operation_Id for correlating all subagent traces in App Insights.

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
        """Generate SSE events from workflow execution.
        
        ADR-007: Events are generated directly by the orchestrator middleware,
        providing real-time updates. OpenTelemetry traces still flow to App Insights
        for observability, but are not used for UI events.
        
        Creates a parent span "research_session" that encompasses the entire
        workflow. This span's operation_Id is used to correlate all traces
        in Application Insights for debugging and dashboards.
        
        Sends heartbeat events every SSE_HEARTBEAT_INTERVAL seconds to prevent
        connection timeouts during long-running agent operations.
        """
        import json
        from datetime import datetime, timezone
        
        # Create parent span for entire research session
        # This provides the operation_Id for all trace correlation in App Insights
        with tracer.start_as_current_span("research_session") as session_span:
            set_session_context(session_span, session_id, session.query)
            session_span.set_attribute("workflow.type", "research")
            
            # Get the trace context for logging/debugging
            span_context = session_span.get_span_context()
            operation_id = format(span_context.trace_id, "032x") if span_context.is_valid else "unknown"
            logger.info(f"=== RESEARCH SESSION START ===")
            logger.info(f"Session ID: {session_id}")
            logger.info(f"Operation ID (trace_id): {operation_id}")
            logger.info(f"Query: {session.query[:100]}...")
            
            # Emit workflow_started with operation_id for trace correlation
            workflow_started_payload = {
                "event_type": "workflow_started",
                "session_id": session_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {
                    "session_id": session_id,
                    "operation_id": operation_id,
                },
            }
            logger.info(f"SSE EMIT: workflow_started - session={session_id[:8]}")
            yield {
                "event": "workflow_started",
                "data": json.dumps(workflow_started_payload),
            }
            
            workflow_gen = orchestrator.run_research_workflow(session_id)
            workflow_exhausted = False
            pending_event_task: asyncio.Task | None = None
            
            try:
                while not workflow_exhausted:
                    # Check if client disconnected
                    if await request.is_disconnected():
                        logger.warning(f"Client disconnected from session {session_id}")
                        session_span.set_attribute("workflow.disconnect", True)
                        break
                    
                    # Create task for next workflow event if not already pending
                    if pending_event_task is None:
                        pending_event_task = asyncio.create_task(workflow_gen.__anext__())
                    
                    # Wait for workflow event or heartbeat timeout
                    done, _ = await asyncio.wait(
                        {pending_event_task},
                        timeout=SSE_HEARTBEAT_INTERVAL,
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    
                    # Process completed workflow event
                    if pending_event_task in done:
                        try:
                            event = pending_event_task.result()
                            # Log high-frequency events at DEBUG, key events at INFO
                            if event.event_type.value in ("subagent_progress", "heartbeat"):
                                logger.debug(f"SSE EMIT: {event.event_type.value} - session={session_id[:8]}")
                            else:
                                logger.info(f"SSE EMIT: {event.event_type.value} - session={session_id[:8]}")
                            yield {
                                "event": event.event_type.value,
                                "data": event.model_dump_json(),
                            }
                            pending_event_task = None  # Clear for next iteration
                        except StopAsyncIteration:
                            logger.info(f"Workflow generator exhausted for session {session_id[:8]}")
                            workflow_exhausted = True
                            pending_event_task = None
                    else:
                        # Timeout - send heartbeat
                        logger.debug(f"SSE EMIT: heartbeat for session {session_id[:8]}")
                        heartbeat_payload = {
                            "event_type": "heartbeat",
                            "session_id": session_id,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "data": {
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            },
                        }
                        yield {
                            "event": "heartbeat",
                            "data": json.dumps(heartbeat_payload),
                        }
                
                session_span.set_attribute("workflow.completed", True)
                logger.info(f"=== RESEARCH SESSION COMPLETE === session={session_id[:8]}")
                        
            except RuntimeError as e:
                # Handle cross-task cancel scope errors from MCP cleanup
                if "cancel scope" in str(e):
                    logger.debug(f"Ignoring cross-task cancel scope during SSE generator: {e}")
                else:
                    logger.exception(f"RuntimeError in workflow for session {session_id}")
                    session_span.record_exception(e)
                    yield {
                        "event": "error",
                        "data": f'{{"error": "{str(e)}"}}',
                    }
            except Exception as e:
                logger.exception(f"Error in workflow for session {session_id}")
                session_span.record_exception(e)
                yield {
                    "event": "error",
                    "data": f'{{"error": "{str(e)}"}}',
                }
            finally:
                # Cancel any pending tasks
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
                
                logger.info(f"SSE generator cleanup complete for session {session_id[:8]}")

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


# === Questions Endpoints (Human-in-the-Loop) ===


@app.get("/research/sessions/{session_id}/questions", response_model=QuestionsResponse, tags=["Research", "Questions"])
async def get_questions(session_id: str, status: str | None = None) -> QuestionsResponse:
    """Get all questions for a session.
    
    Returns questions from agents that need user input. Frontend should poll
    this endpoint to display questions to the user.
    
    Args:
        session_id: The session ID.
        status: Optional filter - 'pending', 'answered', or 'all' (default).

    Returns:
        Questions with workflow status.

    Raises:
        HTTPException: If session not found.
    """
    orchestrator = get_orchestrator()
    session = orchestrator.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    try:
        questions_data = await orchestrator.get_scratchpad_questions(session_id=session_id)
        
        all_questions = questions_data.get("questions", [])
        
        # Apply status filter if provided
        if status == "pending":
            filtered_questions = [q for q in all_questions if not q.get("answered", False)]
        elif status == "answered":
            filtered_questions = [q for q in all_questions if q.get("answered", False)]
        else:
            filtered_questions = all_questions
        
        pending_count = sum(1 for q in all_questions if not q.get("answered", False))
        answered_count = sum(1 for q in all_questions if q.get("answered", False))
        has_blocking_pending = any(
            q.get("priority") == "blocking" and not q.get("answered", False)
            for q in all_questions
        )
        
        # Check if workflow is waiting for input
        workflow_waiting = orchestrator.is_session_waiting_for_input(session_id)
        
        return QuestionsResponse(
            session_id=session_id,
            questions=filtered_questions,
            pending_count=pending_count,
            answered_count=answered_count,
            has_blocking_pending=has_blocking_pending,
            workflow_waiting=workflow_waiting,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.post("/research/sessions/{session_id}/answers", response_model=AnswersResponse, tags=["Research", "Questions"])
async def submit_answers(session_id: str, request: AnswersRequest) -> AnswersResponse:
    """Submit answers to questions and unblock workflow.
    
    Submits user answers to one or more questions. If the workflow is currently
    waiting for user input, this automatically unblocks it.
    
    Args:
        session_id: The session ID.
        request: The answers to submit.

    Returns:
        Result with number of answers saved and workflow status.

    Raises:
        HTTPException: If session not found or error submitting answers.
    """
    orchestrator = get_orchestrator()
    session = orchestrator.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    try:
        # Convert request to format expected by MCP tool
        answers_list = [{"question_id": a.question_id, "answer": a.answer} for a in request.answers]
        
        # Submit answers via MCP scratchpad
        result = await orchestrator.submit_scratchpad_answers(
            session_id=session_id, 
            answers=answers_list
        )
        
        # Check if workflow was waiting and should be unblocked
        workflow_unblocked = False
        if orchestrator.is_session_waiting_for_input(session_id):
            # Unblock the workflow
            orchestrator.unblock_session(session_id)
            workflow_unblocked = True
            logger.info(f"Workflow unblocked for session {session_id}")
        
        return AnswersResponse(
            session_id=session_id,
            answers_saved=result.get("answers_saved", 0),
            workflow_unblocked=workflow_unblocked,
            remaining_pending=result.get("remaining_pending", 0),
        )
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
