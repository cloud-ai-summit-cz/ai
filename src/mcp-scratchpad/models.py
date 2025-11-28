"""Pydantic models for MCP Scratchpad.

These models define the data structures used by the scratchpad.
Designed to be storage-agnostic - can be used with in-memory, Cosmos DB, Redis, etc.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SectionStatus(str, Enum):
    """Status of a scratchpad section."""

    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    NEEDS_REVIEW = "needs_review"
    COMPLETE = "complete"


class ChecklistStatus(str, Enum):
    """Status of a checklist item."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class QuestionPriority(str, Enum):
    """Priority level for human questions."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Section(BaseModel):
    """Named section in scratchpad with collaborative editing support."""

    name: str
    content: str
    status: SectionStatus = SectionStatus.DRAFT
    author: str  # Agent that created it
    contributors: list[str] = Field(default_factory=list)  # Other agents that modified
    version: int = 1
    outline_position: int | None = None  # Position in final report (null if not part of report)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def to_summary(self) -> dict[str, Any]:
        """Return a summary of the section without full content."""
        return {
            "name": self.name,
            "status": self.status.value,
            "author": self.author,
            "contributors": self.contributors,
            "version": self.version,
            "outline_position": self.outline_position,
            "content_length": len(self.content),
            "updated_at": self.updated_at.isoformat(),
        }


class ChecklistItem(BaseModel):
    """Task tracking item."""

    id: str
    task: str
    agent: str
    status: ChecklistStatus = ChecklistStatus.PENDING
    notes: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Question(BaseModel):
    """Question queued for human review."""

    id: str
    question: str
    context: str  # Why this information is needed
    asked_by: str  # Agent that asked
    priority: QuestionPriority = QuestionPriority.MEDIUM
    blocking: bool = False  # If true, workflow should pause for this
    options: list[str] | None = None  # Optional multiple choice
    answer: str | None = None  # Human's answer (null until answered)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    answered_at: datetime | None = None


class ScratchpadSession(BaseModel):
    """Session container for scratchpad data."""

    session_id: str
    sections: dict[str, Section] = Field(default_factory=dict)
    checklist: list[ChecklistItem] = Field(default_factory=list)
    questions: list[Question] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
