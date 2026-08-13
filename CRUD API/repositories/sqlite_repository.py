"""SQLite backend for the TaskRepository interface.

This is the original local-only persistence layer (v2). It is kept so the app
still runs without a database server; the default build uses Postgres instead.
"""

import sqlite3

from repositories.base import TaskRepository


class SqliteTaskRepository(TaskRepository):
    """TaskRepository backed by a single SQLite file on disk."""

    def __init__(self, db_path: str = "tasks.db") -> None:
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        """Open a connection with named columns and WAL mode enabled."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # lets us access columns by name
        conn.execute("PRAGMA journal_mode=WAL")  # better concurrent-read performance
        return conn

    @staticmethod
    def _row_to_task(row: sqlite3.Row) -> dict:
        """Map a sqlite3.Row to the JSON-safe dict clients expect."""
        return {
            "id": row["id"],
            "title": row["title"],
            "done": bool(row["done"]),  # SQLite stores bools as 0/1 integers
        }

    def init(self) -> None:
        """Create the tasks table if it doesn't already exist."""
        with self._connect() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id    INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT    NOT NULL,
                    done  INTEGER NOT NULL DEFAULT 0
                )
                """
            )

    def list(self) -> list[dict]:
        """Return every task in the database."""
        with self._connect() as db:
            rows = db.execute(
                "SELECT id, title, done FROM tasks ORDER BY id"
            ).fetchall()
        return [self._row_to_task(r) for r in rows]

    def get(self, task_id: int) -> dict | None:
        """Return a single task by id, or None."""
        with self._connect() as db:
            row = db.execute(
                "SELECT id, title, done FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
        return self._row_to_task(row) if row is not None else None

    def create(self, title: str) -> dict:
        """Insert a task and return it with its auto-generated id."""
        with self._connect() as db:
            cursor = db.execute(
                "INSERT INTO tasks (title, done) VALUES (?, 0)", (title,)
            )
            row = db.execute(
                "SELECT id, title, done FROM tasks WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()
        return self._row_to_task(row)

    def update(self, task_id: int, title: str | None, done: bool | None) -> dict | None:
        """Partially update a task; return the updated row or None."""
        with self._connect() as db:
            row = db.execute(
                "SELECT id, title, done FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
            if row is None:
                return None

            new_title = title if title is not None else row["title"]
            new_done = int(done) if done is not None else row["done"]

            db.execute(
                "UPDATE tasks SET title = ?, done = ? WHERE id = ?",
                (new_title, new_done, task_id),
            )
            row = db.execute(
                "SELECT id, title, done FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
        return self._row_to_task(row)

    def delete(self, task_id: int) -> bool:
        """Delete a task; return True if a row was removed."""
        with self._connect() as db:
            cursor = db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        return cursor.rowcount > 0
