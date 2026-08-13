"""Task repository interface.

This is the storage abstraction that lets us swap databases without touching
the routes. Every storage backend (SQLite, Postgres, ...) implements these
methods; app.py only ever talks to this interface.
"""

from abc import ABC, abstractmethod


class TaskRepository(ABC):
    """Contract every storage backend must satisfy.

    Methods return plain dicts in the JSON shape the API exposes, so the
    routes never need to know which database is actually behind the scenes.
    """

    @abstractmethod
    def init(self) -> None:
        """Create the tasks table (idempotent — safe to call on every boot)."""

    @abstractmethod
    def list(self) -> list[dict]:
        """Return all tasks ordered by id."""

    @abstractmethod
    def get(self, task_id: int) -> dict | None:
        """Return one task by id, or None if it does not exist."""

    @abstractmethod
    def create(self, title: str) -> dict:
        """Insert a new task and return it with the generated id."""

    @abstractmethod
    def update(self, task_id: int, title: str | None, done: bool | None) -> dict | None:
        """Apply a partial update and return the updated task, or None if missing."""

    @abstractmethod
    def delete(self, task_id: int) -> bool:
        """Delete a task; return True if a row was removed, False otherwise."""