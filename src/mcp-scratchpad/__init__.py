"""MCP Scratchpad Server - Shared workspace for inter-agent collaboration."""

from server import mcp
from config import settings
from storage import StorageBackend, InMemoryStorage, get_storage, set_storage
from models import (
    ScratchpadSession,
    Section,
    SectionStatus,
    ChecklistItem,
    ChecklistStatus,
    Question,
    QuestionPriority,
)

__all__ = [
    "mcp",
    "settings",
    "StorageBackend",
    "InMemoryStorage",
    "get_storage",
    "set_storage",
    "ScratchpadSession",
    "Section",
    "SectionStatus",
    "ChecklistItem",
    "ChecklistStatus",
    "Question",
    "QuestionPriority",
]
