"""FastMCP Server for Scratchpad - Shared workspace for inter-agent collaboration.

SECURITY: Session isolation is enforced via X-Session-ID HTTP header.
The session_id is NOT a tool parameter - it's injected by the orchestrator.
This prevents AI agents from accessing other sessions.

NOTE: Since FastMCP doesn't expose the underlying app for middleware,
we extract session headers in the custom routes and rely on the orchestrator
to pass the correct session_id for tool calls. In debug mode, tools use 'default'.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, List, Optional

from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
from starlette.requests import Request
from starlette.responses import JSONResponse

from config import settings
from models import (
    Note,
    DraftSection,
    Task,
)
from storage import get_storage

logger = logging.getLogger(__name__)

# Thread-local storage for request context (session_id from header)
import contextvars
_request_session_id: contextvars.ContextVar[str] = contextvars.ContextVar('session_id', default='default')
_request_caller_agent: contextvars.ContextVar[str] = contextvars.ContextVar('caller_agent', default='unknown')


def _is_valid_session_id(session_id: str) -> bool:
    """Validate session ID format (UUID or prefixed UUID)."""
    try:
        # Allow bare UUIDs
        uuid.UUID(session_id)
        return True
    except ValueError:
        pass
    
    # Allow prefixed UUIDs like "sess_abc123..."
    if session_id.startswith("sess_"):
        try:
            uuid.UUID(session_id[5:])
            return True
        except ValueError:
            pass
    
    # Allow "default" for development
    if session_id == "default":
        return True
    
    return False


def get_session_id() -> str:
    """Get the current session ID from request context.
    
    SECURITY: This is the ONLY way tools get the session ID.
    It comes from the X-Session-ID header, not from tool parameters.
    """
    return _request_session_id.get()


def get_caller_agent() -> str:
    """Get the calling agent name from request context."""
    return _request_caller_agent.get()


def set_session_context(session_id: str, caller_agent: str = "unknown") -> tuple:
    """Set session context from request headers.
    
    Returns tokens that must be used to reset the context.
    """
    token_session = _request_session_id.set(session_id)
    token_agent = _request_caller_agent.set(caller_agent)
    return token_session, token_agent


def reset_session_context(token_session, token_agent) -> None:
    """Reset session context after request processing."""
    _request_session_id.reset(token_session)
    _request_caller_agent.reset(token_agent)


# Configure authentication with static token verification
auth = StaticTokenVerifier(
    tokens={
        settings.api_key: {
            "client_id": "scratchpad-client",
            "scopes": ["read", "write"],
        }
    }
)

# Create the FastMCP server
mcp = FastMCP(
    name="mcp-scratchpad",
    instructions="""
    Shared workspace for inter-agent collaboration.
    
    The workspace consists of three main pillars:
    1. NOTES: A shared corkboard for raw facts, findings, and snippets. Append-only, unstructured.
    2. DRAFT: The structured manuscript being written. Organized by sections.
    3. PLAN: A shared checklist of tasks to coordinate work.
    
    SECURITY: Session isolation is automatic. You do not need to pass session_id.
    The orchestrator handles session context transparently via HTTP headers.
    """,
    auth=auth,
)


# =============================================================================
# NOTES Tools (The Corkboard)
# =============================================================================

@mcp.tool
def add_note(
    content: str,
    tags: List[str] = [],
) -> dict[str, Any]:
    """Add a raw note, finding, or fact to the shared workspace.
    
    Use this to share information that might be useful for other agents or later in the process.
    Examples: "Competitor X pricing is $10/mo", "Found URL: example.com/report.pdf"
    
    Args:
        content: The content of the note.
        tags: Optional list of tags for categorization.
    
    Note: Session is determined automatically from request context (X-Session-ID header).
    """
    # Get session from request context (injected by middleware)
    session_id = get_session_id()
    agent_id = get_caller_agent()
    
    storage = get_storage()
    session = storage.get_or_create_session(session_id)
    
    note = Note(
        content=content,
        author=agent_id,
        tags=tags
    )
    session.state.notes.append(note)
    storage.save_session(session)
    
    logger.info(f"add_note | session={session_id} | agent={agent_id} | note_id={note.id}")
    
    return {
        "success": True,
        "note_id": note.id,
        "message": "Note added to workspace."
    }

@mcp.tool
def read_notes(
    query: Optional[str] = None,
    tag: Optional[str] = None,
) -> dict[str, Any]:
    """Read notes from the workspace.
    
    Args:
        query: Optional text to search for in note content.
        tag: Optional tag to filter by.
    
    Note: Session is determined automatically from request context (X-Session-ID header).
    """
    # Get session from request context
    session_id = get_session_id()
    
    storage = get_storage()
    session = storage.get_or_create_session(session_id)
    
    results = []
    for note in session.state.notes:
        if tag and tag not in note.tags:
            continue
        if query and query.lower() not in note.content.lower():
            continue
        results.append(note.dict())
        
    return {
        "count": len(results),
        "notes": results
    }


# =============================================================================
# DRAFT Tools (The Manuscript)
# =============================================================================

@mcp.tool
def write_draft_section(
    section_id: str,
    title: str,
    content: str,
) -> dict[str, Any]:
    """Write or overwrite a section of the structured draft.
    
    Args:
        section_id: Unique identifier for the section (e.g., 'executive_summary', 'market_analysis').
        title: Human-readable title.
        content: The full text content of the section.
    
    Note: Session is determined automatically from request context (X-Session-ID header).
    """
    # Get session from request context
    session_id = get_session_id()
    agent_id = get_caller_agent()
    
    storage = get_storage()
    session = storage.get_or_create_session(session_id)
    
    if section_id in session.state.draft_sections:
        # Update existing
        section = session.state.draft_sections[section_id]
        section.title = title
        section.content = content
        section.last_updated = datetime.now()
        section.version += 1
    else:
        # Create new
        section = DraftSection(
            id=section_id,
            title=title,
            content=content
        )
        session.state.draft_sections[section_id] = section
        
    storage.save_session(session)
    
    logger.info(f"write_draft_section | session={session_id} | agent={agent_id} | section={section_id}")
    
    return {
        "success": True,
        "section_id": section_id,
        "version": section.version,
        "message": f"Section '{title}' updated."
    }

@mcp.tool
def read_draft(
    section_id: Optional[str] = None,
) -> dict[str, Any]:
    """Read the current draft.
    
    Args:
        section_id: If provided, returns only that section. If None, returns full draft.
    
    Note: Session is determined automatically from request context (X-Session-ID header).
    """
    # Get session from request context
    session_id = get_session_id()
    
    storage = get_storage()
    session = storage.get_or_create_session(session_id)
    
    if section_id:
        if section_id not in session.state.draft_sections:
            return {"error": "Section not found"}
        return {"section": session.state.draft_sections[section_id].dict()}
    
    # Return full draft sorted by something? For now just dict.
    return {
        "sections": {k: v.dict() for k, v in session.state.draft_sections.items()}
    }


# =============================================================================
# PLAN Tools (The Checklist)
# =============================================================================

@mcp.tool
def add_tasks(
    tasks: List[dict],
) -> dict[str, Any]:
    """Add one or more tasks to the shared plan.
    
    Args:
        tasks: List of task objects, each containing:
            - description (required): What needs to be done
            - dependencies (optional): List of task IDs that must be completed first
        
    Example:
        add_tasks(tasks=[
            {"description": "Research market size"},
            {"description": "Analyze competitors", "dependencies": ["task-1"]},
            {"description": "Write executive summary", "dependencies": ["task-1", "task-2"]}
        ])
    
    Note: Session is determined automatically from request context (X-Session-ID header).
    """
    # Get session from request context
    session_id = get_session_id()
    agent_id = get_caller_agent()
    
    storage = get_storage()
    session = storage.get_or_create_session(session_id)
    
    created_tasks = []
    for task_data in tasks:
        description = task_data.get("description", "")
        if not description:
            continue
        dependencies = task_data.get("dependencies", [])
        
        task = Task(
            description=description,
            dependencies=dependencies
        )
        session.state.plan.append(task)
        created_tasks.append({
            "task_id": task.id,
            "description": description
        })
    
    storage.save_session(session)
    
    logger.info(f"add_tasks | session={session_id} | agent={agent_id} | count={len(created_tasks)}")
    
    return {
        "success": True,
        "tasks_created": len(created_tasks),
        "tasks": created_tasks,
        "message": f"Added {len(created_tasks)} task(s) to plan."
    }

@mcp.tool
def update_task(
    task_id: str,
    status: str,
    assigned_to: Optional[str] = None
) -> dict[str, Any]:
    """Update a task's status or assignment.
    
    Args:
        task_id: The ID of the task.
        status: New status (todo, in_progress, completed, blocked).
        assigned_to: Optional agent ID to assign the task to.
    
    Note: Session is determined automatically from request context (X-Session-ID header).
    """
    # Get session from request context
    session_id = get_session_id()
    agent_id = get_caller_agent()
    
    storage = get_storage()
    session = storage.get_or_create_session(session_id)
    
    found = False
    for task in session.state.plan:
        if task.id == task_id:
            task.status = status
            if assigned_to:
                task.assigned_to = assigned_to
            found = True
            break
            
    if not found:
        return {"error": "Task not found"}
        
    storage.save_session(session)
    
    logger.info(f"update_task | session={session_id} | agent={agent_id} | task={task_id} | status={status}")
    
    return {"success": True, "task_id": task_id, "status": status}

@mcp.tool
def read_plan() -> dict[str, Any]:
    """Read the current plan/checklist.
    
    Note: Session is determined automatically from request context (X-Session-ID header).
    """
    # Get session from request context
    session_id = get_session_id()
    
    storage = get_storage()
    session = storage.get_or_create_session(session_id)
    
    return {
        "tasks": [t.dict() for t in session.state.plan]
    }


# =============================================================================
# Health Check
# =============================================================================


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    """Health check endpoint for load balancers and monitoring."""
    storage = get_storage()
    return JSONResponse({
        "status": "healthy",
        "service": "mcp-scratchpad",
        "sessions": len(storage.list_sessions()),
    })


@mcp.custom_route("/ready", methods=["GET"])
async def readiness_check(request):
    """Readiness check for Kubernetes/Container Apps."""
    return JSONResponse({"status": "ready"})
