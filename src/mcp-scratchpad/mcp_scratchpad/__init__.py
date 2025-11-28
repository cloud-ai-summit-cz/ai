"""MCP Scratchpad Server - Shared workspace for inter-agent collaboration."""

from mcp_scratchpad.server import mcp
from mcp_scratchpad.config import settings
from mcp_scratchpad.storage import StorageBackend, InMemoryStorage, get_storage, set_storage
from mcp_scratchpad.models import (
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
