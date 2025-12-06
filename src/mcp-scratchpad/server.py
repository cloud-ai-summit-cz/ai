"""FastMCP Server for Scratchpad - Shared workspace for inter-agent collaboration.

SECURITY: Session isolation is enforced via X-Session-ID HTTP header.
The session_id is NOT a tool parameter - it's injected by the orchestrator.
This prevents AI agents from accessing other sessions.

Session isolation is implemented using FastMCP middleware to extract
X-Session-ID and X-Caller-Agent headers and store them in context state.
Tools access session context via fastmcp Context.get_state().
"""

import logging
import uuid
from datetime import datetime
from typing import Any, List, Optional

from fastmcp import FastMCP, Context
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
from fastmcp.server.dependencies import get_http_headers
from fastmcp.server.middleware import Middleware, MiddlewareContext
from starlette.requests import Request
from starlette.responses import JSONResponse

from config import settings
from models import (
    Note,
    DraftSection,
    Task,
    Question,
    QuestionPriority,
)
from storage import get_storage

logger = logging.getLogger(__name__)


# =============================================================================
# Session Context Middleware
# =============================================================================

class SessionContextMiddleware(Middleware):
    """Middleware to extract session context from HTTP headers.
    
    Extracts X-Session-ID and X-Caller-Agent headers and stores them
    in FastMCP context state so tools can access them via Context.get_state().
    
    This runs BEFORE tool execution and makes session info available throughout.
    """
    
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        """Extract session headers before any tool is called."""
        # Try to get headers from HTTP request context
        try:
            headers = get_http_headers(include_all=True)
            
            # HTTP headers are case-insensitive, but check both cases to be safe
            # FastMCP/Starlette typically lowercases headers
            session_id = (
                headers.get("x-session-id") or 
                headers.get("X-Session-ID") or 
                "default"
            )
            caller_agent = (
                headers.get("x-caller-agent") or 
                headers.get("X-Caller-Agent") or 
                "unknown"
            )
            
            logger.info(
                f"SessionContextMiddleware.on_call_tool | "
                f"tool={context.message.name} | "
                f"session_id={session_id} | "
                f"caller_agent={caller_agent} | "
                f"all_headers={dict(headers)}"
            )
        except Exception as e:
            logger.warning(f"Could not extract headers: {e}")
            session_id = "default"
            caller_agent = "unknown"
        
        # Store in context state for tools to access
        if context.fastmcp_context:
            context.fastmcp_context.set_state("session_id", session_id)
            context.fastmcp_context.set_state("caller_agent", caller_agent)
            logger.debug(f"Set context state: session_id={session_id}, caller_agent={caller_agent}")
        else:
            logger.warning("No fastmcp_context available to store session state")
        
        # Continue to the tool
        return await call_next(context)


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


def get_session_id_from_context(ctx: Context) -> str:
    """Get session ID from FastMCP context state (set by middleware).
    
    SECURITY: This is the ONLY way tools get the session ID.
    It comes from context state which was set by middleware from HTTP headers.
    This prevents AI agents from accessing other sessions.
    """
    session_id = ctx.get_state("session_id") or "default"
    
    # Validate session ID format
    if not _is_valid_session_id(session_id):
        logger.warning(f"Invalid session ID format: {session_id}, using 'default'")
        return "default"
    
    return session_id


def get_caller_agent_from_context(ctx: Context) -> str:
    """Get caller agent from FastMCP context state (set by middleware)."""
    return ctx.get_state("caller_agent") or "unknown"


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

# Add middleware to extract session context from HTTP headers
mcp.add_middleware(SessionContextMiddleware())


# =============================================================================
# NOTES Tools (The Corkboard)
# =============================================================================

@mcp.tool
def add_note(
    content: str,
    ctx: Context,
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
    # Get session from context state (set by middleware)
    session_id = get_session_id_from_context(ctx)
    agent_id = get_caller_agent_from_context(ctx)
    
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
    ctx: Context,
    query: Optional[str] = None,
    tag: Optional[str] = None,
) -> dict[str, Any]:
    """Read notes from the workspace.
    
    Args:
        query: Optional text to search for in note content.
        tag: Optional tag to filter by.
    
    Note: Session is determined automatically from request context (X-Session-ID header).
    """
    # Get session from context state (set by middleware)
    session_id = get_session_id_from_context(ctx)
    
    storage = get_storage()
    session = storage.get_or_create_session(session_id)
    
    results = []
    for note in session.state.notes:
        if tag and tag not in note.tags:
            continue
        if query and query.lower() not in note.content.lower():
            continue
        results.append(note.model_dump())
    
    logger.info(f"read_notes | session={session_id} | count={len(results)}")
        
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
    ctx: Context,
) -> dict[str, Any]:
    """Write or overwrite a section of the structured draft.
    
    Args:
        section_id: Unique identifier for the section (e.g., 'executive_summary', 'market_analysis').
        title: Human-readable title.
        content: The full text content of the section.
    
    Note: Session is determined automatically from request context (X-Session-ID header).
    """
    # Get session from context state (set by middleware)
    session_id = get_session_id_from_context(ctx)
    agent_id = get_caller_agent_from_context(ctx)
    
    storage = get_storage()
    session = storage.get_or_create_session(session_id)
    
    if section_id in session.state.draft_sections:
        # Update existing
        section = session.state.draft_sections[section_id]
        section.title = title
        section.content = content
        section.author = agent_id  # Track who last updated this section
        section.last_updated = datetime.now()
        section.version += 1
    else:
        # Create new
        section = DraftSection(
            id=section_id,
            title=title,
            content=content,
            author=agent_id,  # Track who created this section
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
    ctx: Context,
    section_id: Optional[str] = None,
) -> dict[str, Any]:
    """Read the current draft.
    
    Args:
        section_id: If provided, returns only that section. If None, returns full draft.
    
    Note: Session is determined automatically from request context (X-Session-ID header).
    """
    # Get session from context state (set by middleware)
    session_id = get_session_id_from_context(ctx)
    
    storage = get_storage()
    session = storage.get_or_create_session(session_id)
    
    logger.info(f"read_draft | session={session_id} | section_count={len(session.state.draft_sections)}")
    
    if section_id:
        if section_id not in session.state.draft_sections:
            return {"error": "Section not found"}
        return {"section": session.state.draft_sections[section_id].model_dump()}
    
    # Return full draft sorted by something? For now just dict.
    return {
        "sections": {k: v.model_dump() for k, v in session.state.draft_sections.items()}
    }


# =============================================================================
# PLAN Tools (The Checklist)
# =============================================================================

@mcp.tool
def add_tasks(
    tasks: List[dict],
    ctx: Context,
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
    # Get session from context state (set by middleware)
    session_id = get_session_id_from_context(ctx)
    agent_id = get_caller_agent_from_context(ctx)
    
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
    ctx: Context,
    assigned_to: Optional[str] = None
) -> dict[str, Any]:
    """Update a task's status or assignment.
    
    Args:
        task_id: The ID of the task.
        status: New status (todo, in_progress, completed, blocked).
        assigned_to: Optional agent ID to assign the task to.
    
    Note: Session is determined automatically from request context (X-Session-ID header).
    """
    # Get session from context state (set by middleware)
    session_id = get_session_id_from_context(ctx)
    agent_id = get_caller_agent_from_context(ctx)
    
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
def read_plan(ctx: Context) -> dict[str, Any]:
    """Read the current plan/checklist.
    
    Note: Session is determined automatically from request context (X-Session-ID header).
    """
    # Get session from context state (set by middleware)
    session_id = get_session_id_from_context(ctx)
    
    storage = get_storage()
    session = storage.get_or_create_session(session_id)
    
    logger.info(f"read_plan | session={session_id} | task_count={len(session.state.plan)}")
    
    return {
        "tasks": [t.model_dump() for t in session.state.plan]
    }


# =============================================================================
# QUESTIONS Tools (Human-in-the-Loop)
# =============================================================================

@mcp.tool
def add_question(
    question: str,
    context: str,
    ctx: Context,
    priority: str = "medium",
) -> dict[str, Any]:
    """Ask a question to the user for clarification or additional input.
    
    Use this when you need information from the user that isn't available
    in the research context. The user can answer asynchronously.
    
    Args:
        question: The question to ask the user.
        context: Why this information is needed (helps user understand importance).
        priority: One of 'low', 'medium', 'high', 'blocking'.
            - low: Nice to have, won't block research
            - medium: Would improve research quality  
            - high: Important for accurate recommendations
            - blocking: Research cannot proceed without answer
    
    Note: Session is determined automatically from request context (X-Session-ID header).
    """
    session_id = get_session_id_from_context(ctx)
    agent_id = get_caller_agent_from_context(ctx)
    
    storage = get_storage()
    session = storage.get_or_create_session(session_id)
    
    # Parse priority
    try:
        question_priority = QuestionPriority(priority.lower())
    except ValueError:
        question_priority = QuestionPriority.MEDIUM
    
    q = Question(
        question=question,
        context=context,
        asked_by=agent_id,
        priority=question_priority,
    )
    session.state.questions.append(q)
    storage.save_session(session)
    
    logger.info(f"add_question | session={session_id} | agent={agent_id} | priority={priority} | question_id={q.id}")
    
    return {
        "success": True,
        "question_id": q.id,
        "priority": question_priority.value,
        "message": f"Question added. User will be notified to answer."
    }


@mcp.tool
def get_pending_questions(ctx: Context) -> dict[str, Any]:
    """Get all unanswered questions for this session.
    
    Use this to check if there are questions waiting for user answers.
    
    Note: Session is determined automatically from request context (X-Session-ID header).
    """
    session_id = get_session_id_from_context(ctx)
    
    storage = get_storage()
    session = storage.get_or_create_session(session_id)
    
    pending = [q for q in session.state.questions if not q.answered]
    
    logger.info(f"get_pending_questions | session={session_id} | count={len(pending)}")
    
    return {
        "count": len(pending),
        "questions": [q.model_dump() for q in pending]
    }


@mcp.tool
def get_answered_questions(ctx: Context) -> dict[str, Any]:
    """Get all answered questions with their answers.
    
    Use this to review user answers to previously asked questions.
    
    Note: Session is determined automatically from request context (X-Session-ID header).
    """
    session_id = get_session_id_from_context(ctx)
    
    storage = get_storage()
    session = storage.get_or_create_session(session_id)
    
    answered = [q for q in session.state.questions if q.answered]
    
    logger.info(f"get_answered_questions | session={session_id} | count={len(answered)}")
    
    return {
        "count": len(answered),
        "questions": [q.model_dump() for q in answered]
    }


@mcp.tool
def get_all_questions(ctx: Context) -> dict[str, Any]:
    """Get all questions (pending and answered) for this session.
    
    Note: Session is determined automatically from request context (X-Session-ID header).
    """
    session_id = get_session_id_from_context(ctx)
    
    storage = get_storage()
    session = storage.get_or_create_session(session_id)
    
    all_questions = session.state.questions
    pending_count = sum(1 for q in all_questions if not q.answered)
    answered_count = sum(1 for q in all_questions if q.answered)
    
    logger.info(f"get_all_questions | session={session_id} | total={len(all_questions)} | pending={pending_count}")
    
    return {
        "total": len(all_questions),
        "pending_count": pending_count,
        "answered_count": answered_count,
        "questions": [q.model_dump() for q in all_questions]
    }


@mcp.tool
def submit_answers(
    answers: List[dict],
    ctx: Context,
) -> dict[str, Any]:
    """Submit answers to pending questions.
    
    This is typically called by the orchestrator when the user submits
    answers through the UI.
    
    Args:
        answers: List of answer objects, each containing:
            - question_id (required): ID of the question being answered
            - answer (required): The user's answer
    
    Note: Session is determined automatically from request context (X-Session-ID header).
    """
    session_id = get_session_id_from_context(ctx)
    
    storage = get_storage()
    session = storage.get_or_create_session(session_id)
    
    answered_count = 0
    answered_ids = []
    
    # Build a map of question IDs for quick lookup
    question_map = {q.id: q for q in session.state.questions}
    
    for answer_data in answers:
        question_id = answer_data.get("question_id")
        answer_text = answer_data.get("answer")
        
        if not question_id or not answer_text:
            continue
            
        if question_id in question_map:
            q = question_map[question_id]
            if not q.answered:  # Don't overwrite existing answers
                q.answer = answer_text
                q.answered = True
                q.answered_at = datetime.now()
                answered_count += 1
                answered_ids.append(question_id)
    
    storage.save_session(session)
    
    # Check remaining pending questions
    remaining_pending = sum(1 for q in session.state.questions if not q.answered)
    has_blocking_pending = any(
        q.priority == QuestionPriority.BLOCKING and not q.answered 
        for q in session.state.questions
    )
    
    logger.info(f"submit_answers | session={session_id} | answered={answered_count} | remaining_pending={remaining_pending}")
    
    return {
        "success": True,
        "answers_saved": answered_count,
        "answered_ids": answered_ids,
        "remaining_pending": remaining_pending,
        "has_blocking_pending": has_blocking_pending,
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
