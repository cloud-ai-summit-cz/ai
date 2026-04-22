from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
import uuid

class Note(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    content: str
    author: str  # The name of the agent who created it
    timestamp: datetime = Field(default_factory=datetime.now)
    tags: List[str] = Field(default_factory=list)

class DraftSection(BaseModel):
    id: str
    title: str
    content: str
    last_updated: datetime = Field(default_factory=datetime.now)
    version: int = 1

class TaskStatus(str):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"

class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str
    status: str = "todo"  # simple string to avoid enum serialization complexity in simple dicts
    assigned_to: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)  # IDs of other tasks

class WorkspaceState(BaseModel):
    notes: List[Note] = Field(default_factory=list)
    draft_sections: Dict[str, DraftSection] = Field(default_factory=dict)
    plan: List[Task] = Field(default_factory=list)
