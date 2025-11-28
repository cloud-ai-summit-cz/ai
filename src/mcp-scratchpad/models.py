"""Pydantic models for MCP Scratchpad.

These models define the data structures used by the scratchpad.
Designed to be storage-agnostic - can be used with in-memory, Cosmos DB, Redis, etc.
"""

from datetime import datetime
from typing import Dict, List, Optional
import uuid

from pydantic import BaseModel, Field


class Note(BaseModel):
    """A raw piece of information, fact, or finding."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    content: str
    author: str  # The name of the agent who created it
    timestamp: datetime = Field(default_factory=datetime.now)
    tags: List[str] = Field(default_factory=list)


class DraftSection(BaseModel):
    """A structured section of the final report/output."""
    id: str
    title: str
    content: str
    last_updated: datetime = Field(default_factory=datetime.now)
    version: int = 1


class Task(BaseModel):
    """A unit of work to be done."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str
    status: str = "todo"  # todo, in_progress, completed, blocked
    assigned_to: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)  # IDs of other tasks


class WorkspaceState(BaseModel):
    """The core state of the workspace."""
    notes: List[Note] = Field(default_factory=list)
    draft_sections: Dict[str, DraftSection] = Field(default_factory=dict)
    plan: List[Task] = Field(default_factory=list)


class ScratchpadSession(BaseModel):
    """Session container for scratchpad data."""
    session_id: str
    state: WorkspaceState = Field(default_factory=WorkspaceState)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
