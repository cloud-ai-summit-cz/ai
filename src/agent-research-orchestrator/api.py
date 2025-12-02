"""FastAPI REST API for Research Orchestrator.

Exposes REST endpoints and SSE streaming for the research workflow.

Includes App Insights trace polling (ADR-005) for real-time visibility
into subagent tool calls that can't be captured via MAF stream_callback.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from opentelemetry import trace
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
from telemetry import get_tracer, set_session_context
from trace_poller import AppInsightsTracePoller

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
    """Detailed health check including trace polling status."""
    orchestrator = get_orchestrator()
    settings = get_settings()
    health_data = await orchestrator.check_health()

    return {
        "status": "healthy",
        "version": __version__,
        "foundry_endpoint": health_data["foundry_endpoint"],
        "model_deployment": health_data["model_deployment"],
        "mcp_scratchpad": health_data.get("mcp_scratchpad"),
        "trace_polling": {
            "enabled": settings.trace_polling_enabled,
            "configured": settings.trace_polling_configured,
            "workspace_id": settings.log_analytics_workspace_id[:8] + "..." if settings.log_analytics_workspace_id else None,
            "interval_seconds": settings.trace_polling_interval_seconds,
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
        """Generate SSE events from workflow execution with trace polling.
        
        Creates a parent span "research_session" that encompasses the entire
        workflow. This span's operation_Id is used to correlate all subagent
        traces in Application Insights (ADR-005).
        
        Implements two parallel event sources:
        1. Workflow events from orchestrator.run_research_workflow()
        2. Trace events from App Insights polling (if configured)
        
        Sends heartbeat events every SSE_HEARTBEAT_INTERVAL seconds to prevent
        connection timeouts during long-running agent operations.
        """
        import json
        from datetime import datetime, timezone
        
        settings = get_settings()
        
        # Create parent span for entire research session
        # This provides the operation_Id for all subagent trace correlation
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
            logger.info(f"Span context valid: {span_context.is_valid}")
            
            # Check if trace polling is configured
            trace_polling_active = settings.trace_polling_configured
            logger.info(f"=== TRACE POLLING CONFIG ===")
            logger.info(f"trace_polling_enabled setting: {settings.trace_polling_enabled}")
            logger.info(f"log_analytics_workspace_id: {settings.log_analytics_workspace_id or 'NOT SET'}")
            logger.info(f"trace_polling_configured (computed): {settings.trace_polling_configured}")
            logger.info(f"trace_polling_active (will use): {trace_polling_active}")
            
            if trace_polling_active:
                logger.info(
                    f"Trace polling ENABLED for session {session_id}: "
                    f"workspace_id={settings.log_analytics_workspace_id}, "
                    f"interval={settings.trace_polling_interval_seconds}s"
                )
            else:
                logger.info(
                    f"Trace polling DISABLED for session {session_id}: "
                    f"LOG_ANALYTICS_WORKSPACE_ID not configured or polling disabled"
                )
            
            # Emit operation_id as first event so frontend can track it
            workflow_started_payload = {
                "event_type": "workflow_started",
                "session_id": session_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {
                    "session_id": session_id,
                    "operation_id": operation_id,
                    "trace_polling_enabled": trace_polling_active,
                },
            }
            logger.info(f"SSE EMIT: workflow_started - {workflow_started_payload}")
            yield {
                "event": "workflow_started",
                "data": json.dumps(workflow_started_payload),
            }
            
            workflow_gen = orchestrator.run_research_workflow(session_id)
            workflow_exhausted = False
            pending_event_task: asyncio.Task | None = None
            trace_poller: AppInsightsTracePoller | None = None
            trace_poll_task: asyncio.Task | None = None
            
            try:
                # Initialize trace poller if configured
                if trace_polling_active:
                    logger.info(f"=== INITIALIZING TRACE POLLER ===")
                    logger.info(f"Workspace ID: {settings.log_analytics_workspace_id}")
                    logger.info(f"Session ID: {session_id}")
                    logger.info(f"Operation ID: {operation_id}")
                    try:
                        trace_poller = AppInsightsTracePoller(
                            workspace_id=settings.log_analytics_workspace_id,
                            session_id=session_id,
                            operation_id=operation_id,
                        )
                        await trace_poller.__aenter__()
                        logger.info(f"Trace poller initialized successfully for session {session_id}")
                    except Exception as e:
                        logger.error(f"Failed to initialize trace poller: {e}")
                        import traceback
                        logger.error(f"Trace poller init traceback: {traceback.format_exc()}")
                        trace_poller = None
                else:
                    logger.info(f"Skipping trace poller initialization (not configured)")
                
                while not workflow_exhausted:
                    # Check if client disconnected
                    if await request.is_disconnected():
                        logger.warning(f"Client disconnected from session {session_id}")
                        session_span.set_attribute("workflow.disconnect", True)
                        break
                    
                    # Create task for next workflow event if not already pending
                    if pending_event_task is None:
                        pending_event_task = asyncio.create_task(workflow_gen.__anext__())
                    
                    # Create task for trace polling if poller is active and no poll pending
                    if trace_poller and trace_poll_task is None:
                        trace_poll_task = asyncio.create_task(trace_poller.poll_once())
                    
                    # Build set of tasks to wait on
                    tasks_to_wait: set[asyncio.Task] = {pending_event_task}
                    if trace_poll_task:
                        tasks_to_wait.add(trace_poll_task)
                    
                    # Wait for any task or heartbeat timeout
                    done, _ = await asyncio.wait(
                        tasks_to_wait,
                        timeout=SSE_HEARTBEAT_INTERVAL,
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    
                    # Process completed workflow event
                    if pending_event_task in done:
                        try:
                            event = pending_event_task.result()
                            logger.info(f"SSE EMIT (workflow): {event.event_type.value} - session={session_id[:8]}")
                            logger.debug(f"SSE EMIT (workflow) data: {event.model_dump_json()[:500]}")
                            yield {
                                "event": event.event_type.value,
                                "data": event.model_dump_json(),
                            }
                            pending_event_task = None  # Clear for next iteration
                        except StopAsyncIteration:
                            logger.info(f"Workflow generator exhausted for session {session_id[:8]}...")
                            workflow_exhausted = True
                            pending_event_task = None
                    
                    # Process completed trace poll
                    if trace_poll_task and trace_poll_task in done:
                        logger.info(f"=== TRACE POLL COMPLETED ===")
                        try:
                            trace_events = trace_poll_task.result()
                            logger.info(f"Trace poll returned {len(trace_events)} events")
                            if trace_events:
                                logger.info(f"SSE EMIT (trace): {len(trace_events)} trace events for session {session_id}")
                            else:
                                logger.info(f"No trace events found in this poll cycle")
                            for trace_event in trace_events:
                                logger.info(
                                    f"SSE EMIT (trace): {trace_event.event_type.value} - "
                                    f"data={trace_event.data}"
                                )
                                yield {
                                    "event": trace_event.event_type.value,
                                    "data": trace_event.model_dump_json(),
                                }
                        except Exception as e:
                            logger.warning(f"Trace poll failed: {e}")
                            import traceback
                            logger.warning(f"Trace poll traceback: {traceback.format_exc()}")
                        finally:
                            trace_poll_task = None
                            # Schedule next poll after interval
                            if trace_poller and not workflow_exhausted:
                                logger.info(f"Scheduling next trace poll in {settings.trace_polling_interval_seconds}s")
                                await asyncio.sleep(settings.trace_polling_interval_seconds)
                    
                    # If nothing completed, send heartbeat
                    if not done:
                        logger.info(f"SSE EMIT: heartbeat for session {session_id[:8]}")
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
                
                # Workflow complete - do one final trace poll to catch remaining spans
                if trace_poller:
                    logger.info(f"Workflow complete, doing final trace poll for session {session_id[:8]}...")
                    try:
                        # Wait a bit for final traces to be ingested
                        await asyncio.sleep(2.0)
                        final_traces = await trace_poller.poll_once()
                        for trace_event in final_traces:
                            yield {
                                "event": trace_event.event_type.value,
                                "data": trace_event.model_dump_json(),
                            }
                        logger.info(f"Final trace poll yielded {len(final_traces)} events")
                    except Exception as e:
                        logger.warning(f"Final trace poll failed: {e}")
                
                session_span.set_attribute("workflow.completed", True)
                        
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
                
                if trace_poll_task and not trace_poll_task.done():
                    trace_poll_task.cancel()
                    try:
                        await trace_poll_task
                    except asyncio.CancelledError:
                        pass
                
                # Cleanup trace poller
                if trace_poller:
                    try:
                        await trace_poller.__aexit__(None, None, None)
                    except Exception as e:
                        logger.debug(f"Error closing trace poller: {e}")
                
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
                
                logger.info(f"SSE generator cleanup complete for session {session_id[:8]}...")

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
