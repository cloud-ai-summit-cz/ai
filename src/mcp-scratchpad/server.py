"""FastMCP Server for Scratchpad - Shared workspace for inter-agent collaboration."""

import uuid
from datetime import datetime
from typing import Any

from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
from starlette.responses import JSONResponse

from config import settings
from models import (
    ChecklistItem,
    ChecklistStatus,
    Question,
    QuestionPriority,
    Section,
    SectionStatus,
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
    Shared workspace for inter-agent collaboration, document building, and human question queue.
    
    Use this MCP server to:
    - Store and retrieve research findings in named sections
    - Track progress with checklist items  
    - Queue questions for human review
    - Build collaborative documents across multiple agents
    
    Session ID is required for all operations and should be passed in the request context.
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
# Section Management Tools
# =============================================================================


@mcp.tool
def read_section(section_name: str, session_id: str = "default") -> dict[str, Any]:
    """Read content from a named section in the scratchpad.
    
    Args:
        section_name: Name of the section to read (e.g., 'market_findings', 'competitor_analysis')
        session_id: Session ID for the scratchpad
        
    Returns:
        Section data including content, status, author, and metadata
    """
    storage = get_storage()
    session = storage.get_or_create_session(session_id)
    
    if section_name not in session.sections:
        return {"error": f"Section '{section_name}' not found", "exists": False}
    
    section = session.sections[section_name]
    return {
        "exists": True,
        "name": section.name,
        "content": section.content,
        "status": section.status.value,
        "author": section.author,
        "contributors": section.contributors,
        "version": section.version,
        "outline_position": section.outline_position,
        "created_at": section.created_at.isoformat(),
        "updated_at": section.updated_at.isoformat(),
    }


@mcp.tool
def write_section(
    section_name: str,
    content: str,
    session_id: str = "default",
    agent_id: str = "unknown",
    status: str = "draft",
    outline_position: int | None = None,
) -> dict[str, Any]:
    """Write or overwrite content to a named section.
    
    Args:
        section_name: Name of the section to write
        content: Content to write to the section
        session_id: Session ID for the scratchpad
        agent_id: ID of the agent writing the section
        status: Status of the section (draft, in_progress, needs_review, complete)
        outline_position: Position in final report outline (1-based), null if not part of report
        
    Returns:
        Confirmation with section metadata
    """
    storage = get_storage()
    session = storage.get_or_create_session(session_id)
    
    try:
        section_status = SectionStatus(status)
    except ValueError:
        section_status = SectionStatus.DRAFT
    
    now = datetime.utcnow()
    
    if section_name in session.sections:
        # Update existing section
        existing = session.sections[section_name]
        existing.content = content
        existing.status = section_status
        existing.version += 1
        existing.updated_at = now
        existing.outline_position = outline_position
        if agent_id not in existing.contributors and agent_id != existing.author:
            existing.contributors.append(agent_id)
        is_new = False
    else:
        # Create new section
        session.sections[section_name] = Section(
            name=section_name,
            content=content,
            status=section_status,
            author=agent_id,
            outline_position=outline_position,
            created_at=now,
            updated_at=now,
        )
        is_new = True
    
    storage.save_session(session)
    section = session.sections[section_name]
    
    return {
        "success": True,
        "is_new": is_new,
        "name": section.name,
        "version": section.version,
        "status": section.status.value,
        "updated_at": section.updated_at.isoformat(),
    }


@mcp.tool
def append_to_section(
    section_name: str,
    content: str,
    session_id: str = "default",
    agent_id: str = "unknown",
) -> dict[str, Any]:
    """Append content to an existing section without overwriting.
    
    Args:
        section_name: Name of the section to append to
        content: Content to append
        session_id: Session ID for the scratchpad
        agent_id: ID of the agent appending content
        
    Returns:
        Confirmation with updated section metadata
    """
    storage = get_storage()
    session = storage.get_or_create_session(session_id)
    
    if section_name not in session.sections:
        return {"error": f"Section '{section_name}' not found", "success": False}
    
    section = session.sections[section_name]
    section.content += "\n" + content
    section.version += 1
    section.updated_at = datetime.utcnow()
    
    if agent_id not in section.contributors and agent_id != section.author:
        section.contributors.append(agent_id)
    
    storage.save_session(session)
    
    return {
        "success": True,
        "name": section.name,
        "version": section.version,
        "content_length": len(section.content),
        "updated_at": section.updated_at.isoformat(),
    }


@mcp.tool
def list_sections(session_id: str = "default") -> dict[str, Any]:
    """List all sections in the current session scratchpad with their metadata.
    
    Args:
        session_id: Session ID for the scratchpad
        
    Returns:
        List of section summaries (without full content)
    """
    storage = get_storage()
    session = storage.get_or_create_session(session_id)
    
    sections = [section.to_summary() for section in session.sections.values()]
    
    return {
        "session_id": session_id,
        "section_count": len(sections),
        "sections": sections,
    }


# =============================================================================
# Checklist Tools
# =============================================================================


@mcp.tool
def get_checklist(session_id: str = "default") -> dict[str, Any]:
    """Get the current state of the research checklist.
    
    Args:
        session_id: Session ID for the scratchpad
        
    Returns:
        List of checklist items with their status
    """
    storage = get_storage()
    session = storage.get_or_create_session(session_id)
    
    items = [
        {
            "id": item.id,
            "task": item.task,
            "agent": item.agent,
            "status": item.status.value,
            "notes": item.notes,
            "updated_at": item.updated_at.isoformat(),
        }
        for item in session.checklist
    ]
    
    return {
        "session_id": session_id,
        "item_count": len(items),
        "items": items,
    }


@mcp.tool
def update_checklist(
    item_id: str,
    status: str,
    session_id: str = "default",
    notes: str | None = None,
) -> dict[str, Any]:
    """Update the status of a checklist item.
    
    Args:
        item_id: ID of the checklist item
        status: New status (pending, in_progress, completed, failed)
        session_id: Session ID for the scratchpad
        notes: Optional notes about the status change
        
    Returns:
        Updated checklist item or error
    """
    storage = get_storage()
    session = storage.get_or_create_session(session_id)
    
    try:
        new_status = ChecklistStatus(status)
    except ValueError:
        return {"error": f"Invalid status: {status}", "success": False}
    
    for item in session.checklist:
        if item.id == item_id:
            old_status = item.status
            item.status = new_status
            item.updated_at = datetime.utcnow()
            if notes:
                item.notes = notes
            storage.save_session(session)
            return {
                "success": True,
                "id": item.id,
                "old_status": old_status.value,
                "new_status": item.status.value,
                "notes": item.notes,
            }
    
    return {"error": f"Checklist item '{item_id}' not found", "success": False}


@mcp.tool
def add_checklist_item(
    task: str,
    agent: str,
    session_id: str = "default",
    item_id: str | None = None,
) -> dict[str, Any]:
    """Add a new item to the checklist.
    
    Args:
        task: Description of the task
        agent: Agent responsible for the task
        session_id: Session ID for the scratchpad
        item_id: Optional custom ID (auto-generated if not provided)
        
    Returns:
        Created checklist item
    """
    storage = get_storage()
    session = storage.get_or_create_session(session_id)
    
    if item_id is None:
        item_id = f"task_{len(session.checklist) + 1}"
    
    item = ChecklistItem(
        id=item_id,
        task=task,
        agent=agent,
    )
    session.checklist.append(item)
    storage.save_session(session)
    
    return {
        "success": True,
        "id": item.id,
        "task": item.task,
        "agent": item.agent,
        "status": item.status.value,
    }


# =============================================================================
# Question Tools
# =============================================================================


@mcp.tool
def add_question(
    question: str,
    context: str,
    session_id: str = "default",
    agent_id: str = "unknown",
    priority: str = "medium",
    blocking: bool = False,
    options: list[str] | None = None,
) -> dict[str, Any]:
    """Add a question for human review.
    
    Args:
        question: The question to ask the human
        context: Why this information is needed (helps user provide better answer)
        session_id: Session ID for the scratchpad
        agent_id: ID of the agent asking the question
        priority: Priority level (high, medium, low)
        blocking: If true, workflow should pause until answered
        options: Optional multiple choice options
        
    Returns:
        Created question with ID
    """
    storage = get_storage()
    session = storage.get_or_create_session(session_id)
    
    try:
        q_priority = QuestionPriority(priority)
    except ValueError:
        q_priority = QuestionPriority.MEDIUM
    
    question_id = f"q_{uuid.uuid4().hex[:8]}"
    
    q = Question(
        id=question_id,
        question=question,
        context=context,
        asked_by=agent_id,
        priority=q_priority,
        blocking=blocking,
        options=options,
    )
    session.questions.append(q)
    storage.save_session(session)
    
    return {
        "success": True,
        "id": q.id,
        "question": q.question,
        "priority": q.priority.value,
        "blocking": q.blocking,
    }


@mcp.tool
def get_pending_questions(session_id: str = "default") -> dict[str, Any]:
    """Get all questions that haven't been answered yet.
    
    Args:
        session_id: Session ID for the scratchpad
        
    Returns:
        List of pending questions
    """
    storage = get_storage()
    session = storage.get_or_create_session(session_id)
    
    pending = [
        {
            "id": q.id,
            "question": q.question,
            "context": q.context,
            "asked_by": q.asked_by,
            "priority": q.priority.value,
            "blocking": q.blocking,
            "options": q.options,
            "created_at": q.created_at.isoformat(),
        }
        for q in session.questions
        if q.answer is None
    ]
    
    has_blocking = any(q["blocking"] for q in pending)
    
    return {
        "session_id": session_id,
        "count": len(pending),
        "has_blocking": has_blocking,
        "questions": pending,
    }


@mcp.tool
def get_answered_questions(session_id: str = "default") -> dict[str, Any]:
    """Get questions that have been answered by the human.
    
    Args:
        session_id: Session ID for the scratchpad
        
    Returns:
        List of answered questions with their answers
    """
    storage = get_storage()
    session = storage.get_or_create_session(session_id)
    
    answered = [
        {
            "id": q.id,
            "question": q.question,
            "answer": q.answer,
            "asked_by": q.asked_by,
            "answered_at": q.answered_at.isoformat() if q.answered_at else None,
        }
        for q in session.questions
        if q.answer is not None
    ]
    
    return {
        "session_id": session_id,
        "count": len(answered),
        "questions": answered,
    }


@mcp.tool
def submit_answers(
    answers: dict[str, str],
    session_id: str = "default",
) -> dict[str, Any]:
    """Submit answers to pending questions.
    
    Args:
        answers: Map of question_id to answer string
        session_id: Session ID for the scratchpad
        
    Returns:
        Summary of submitted answers
    """
    storage = get_storage()
    session = storage.get_or_create_session(session_id)
    
    now = datetime.utcnow()
    answered_ids = []
    not_found = []
    
    for question_id, answer in answers.items():
        found = False
        for q in session.questions:
            if q.id == question_id:
                q.answer = answer
                q.answered_at = now
                answered_ids.append(question_id)
                found = True
                break
        if not found:
            not_found.append(question_id)
    
    storage.save_session(session)
    
    # Also write answers to a special section for agents to read
    if answered_ids:
        answers_content = "\n".join(
            f"Q: {q.question}\nA: {q.answer}"
            for q in session.questions
            if q.answer is not None
        )
        if "user_answers" not in session.sections:
            session.sections["user_answers"] = Section(
                name="user_answers",
                content=answers_content,
                author="human",
                status=SectionStatus.COMPLETE,
            )
        else:
            session.sections["user_answers"].content = answers_content
            session.sections["user_answers"].version += 1
            session.sections["user_answers"].updated_at = now
        storage.save_session(session)
    
    return {
        "success": True,
        "answered_count": len(answered_ids),
        "answered_ids": answered_ids,
        "not_found": not_found,
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
