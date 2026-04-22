"""Storage abstraction layer for MCP Scratchpad.

Provides a protocol-based interface for storage backends.
Current implementation: In-memory storage.
Future implementations: Cosmos DB, Redis, etc.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Protocol

from models import (
    ScratchpadSession,
)


class StorageBackend(Protocol):
    """Protocol defining the storage interface."""

    def get_session(self, session_id: str) -> ScratchpadSession | None:
        """Get a session by ID."""
        ...

    def get_or_create_session(self, session_id: str) -> ScratchpadSession:
        """Get existing session or create a new one."""
        ...

    def save_session(self, session: ScratchpadSession) -> None:
        """Save/update a session."""
        ...

    def delete_session(self, session_id: str) -> bool:
        """Delete a session. Returns True if deleted, False if not found."""
        ...

    def list_sessions(self) -> list[str]:
        """List all session IDs."""
        ...


class InMemoryStorage:
    """In-memory storage implementation.
    
    Thread-safe for basic operations within a single process.
    Data is lost on service restart.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, ScratchpadSession] = {}

    def get_session(self, session_id: str) -> ScratchpadSession | None:
        """Get a session by ID."""
        return self._sessions.get(session_id)

    def get_or_create_session(self, session_id: str) -> ScratchpadSession:
        """Get existing session or create a new one."""
        if session_id not in self._sessions:
            self._sessions[session_id] = ScratchpadSession(session_id=session_id)
        return self._sessions[session_id]

    def save_session(self, session: ScratchpadSession) -> None:
        """Save/update a session."""
        session.updated_at = datetime.utcnow()
        self._sessions[session.session_id] = session

    def delete_session(self, session_id: str) -> bool:
        """Delete a session. Returns True if deleted, False if not found."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def list_sessions(self) -> list[str]:
        """List all session IDs."""
        return list(self._sessions.keys())


# Global storage instance - can be swapped for different backends
_storage: StorageBackend = InMemoryStorage()


def get_storage() -> StorageBackend:
    """Get the current storage backend."""
    return _storage


def set_storage(storage: StorageBackend) -> None:
    """Set a custom storage backend (for testing or production use)."""
    global _storage
    _storage = storage
