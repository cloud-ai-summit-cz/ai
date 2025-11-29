"""FastMCP Server for Scratchpad - Shared workspace for inter-agent collaboration."""

import uuid
from datetime import datetime
from typing import Any, List, Optional

from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
from starlette.responses import JSONResponse

from config import settings
from models import (
    Note,
    DraftSection,
    Task,
)
from storage import get_storage

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
    
    Session ID is required for all operations.
    """,
    auth=auth,
)


def _get_session_id(context: dict[str, Any] | None = None) -> str:
    """Extract session_id from context or use default."""
    if context and "session_id" in context:
        return context["session_id"]
    # Default session for testing/development
    return "default"


def _get_agent_id(context: dict[str, Any] | None = None) -> str:
    """Extract agent_id from context or use default."""
    if context and "agent_id" in context:
        return context["agent_id"]
    return "unknown"


# =============================================================================
# NOTES Tools (The Corkboard)
# =============================================================================

@mcp.tool
def add_note(
    content: str,
    tags: List[str] = [],
    session_id: str = "default",
    agent_id: str = "unknown",
) -> dict[str, Any]:
    """Add a raw note, finding, or fact to the shared workspace.
    
    Use this to share information that might be useful for other agents or later in the process.
    Examples: "Competitor X pricing is $10/mo", "Found URL: example.com/report.pdf"
    
    Args:
        content: The content of the note.
        tags: Optional list of tags for categorization.
        session_id: Session ID.
        agent_id: ID of the agent creating the note.
    """
    storage = get_storage()
    session = storage.get_or_create_session(session_id)
    
    note = Note(
        content=content,
        author=agent_id,
        tags=tags
    )
    session.state.notes.append(note)
    storage.save_session(session)
    
    return {
        "success": True,
        "note_id": note.id,
        "message": "Note added to workspace."
    }

@mcp.tool
def read_notes(
    query: Optional[str] = None,
    tag: Optional[str] = None,
    session_id: str = "default"
) -> dict[str, Any]:
    """Read notes from the workspace.
    
    Args:
        query: Optional text to search for in note content.
        tag: Optional tag to filter by.
        session_id: Session ID.
    """
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
    session_id: str = "default"
) -> dict[str, Any]:
    """Write or overwrite a section of the structured draft.
    
    Args:
        section_id: Unique identifier for the section (e.g., 'executive_summary', 'market_analysis').
        title: Human-readable title.
        content: The full text content of the section.
        session_id: Session ID.
    """
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
    
    return {
        "success": True,
        "section_id": section_id,
        "version": section.version,
        "message": f"Section '{title}' updated."
    }

@mcp.tool
def read_draft(
    section_id: Optional[str] = None,
    session_id: str = "default"
) -> dict[str, Any]:
    """Read the current draft.
    
    Args:
        section_id: If provided, returns only that section. If None, returns full draft.
        session_id: Session ID.
    """
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
    session_id: str = "default"
) -> dict[str, Any]:
    """Add one or more tasks to the shared plan.
    
    Args:
        tasks: List of task objects, each containing:
            - description (required): What needs to be done
            - dependencies (optional): List of task IDs that must be completed first
        session_id: Session ID.
        
    Example:
        add_tasks(tasks=[
            {"description": "Research market size"},
            {"description": "Analyze competitors", "dependencies": ["task-1"]},
            {"description": "Write executive summary", "dependencies": ["task-1", "task-2"]}
        ])
    """
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
    session_id: str = "default",
    assigned_to: Optional[str] = None
) -> dict[str, Any]:
    """Update a task's status or assignment.
    
    Args:
        task_id: The ID of the task.
        status: New status (todo, in_progress, completed, blocked).
        assigned_to: Optional agent ID to assign the task to.
        session_id: Session ID.
    """
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
    return {"success": True, "task_id": task_id, "status": status}

@mcp.tool
def read_plan(session_id: str = "default") -> dict[str, Any]:
    """Read the current plan/checklist.
    
    Args:
        session_id: Session ID.
    """
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
