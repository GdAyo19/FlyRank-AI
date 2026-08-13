"""Postgres backend for the TaskRepository interface.

This is the production storage layer (v3). It speaks the exact same interface
as the SQLite backend, so swapping storage is just a change in `.env` — the
routes in app.py never change.
"""

import psycopg
from psycopg.rows import dict_row

from repositories.base import TaskRepository


class PostgresTaskRepository(TaskRepository):
    """TaskRepository backed by a Postgres database."""

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    def _connect(self) -> psycopg.Connection:
        """Open a connection and read columns by name (rows come back as dicts)."""
        conn = psycopg.connect(self.dsn)
        conn.row_factory = dict_row  # rows become dicts keyed by column name
        return conn

    def init(self) -> None:
        """Create the tasks table if it doesn't already exist."""
        with self._connect() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id    SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    done  BOOLEAN NOT NULL DEFAULT FALSE
                )
                """
            )

    def list(self) -> list[dict]:
        """Return every task in the database."""
        with self._connect() as db:
            rows = db.execute(
                "SELECT id, title, done FROM tasks ORDER BY id"
            ).fetchall()
        return [dict(r) for r in rows]

    def get(self, task_id: int) -> dict | None:
        """Return a single task by id, or None."""
        with self._connect() as db:
            row = db.execute(
                "SELECT id, title, done FROM tasks WHERE id = %s", (task_id,)
            ).fetchone()
        return dict(row) if row is not None else None

    def create(self, title: str) -> dict:
        """Insert a task and return it with the server-generated id."""
        with self._connect() as db:
            row = db.execute(
                """
                INSERT INTO tasks (title) VALUES (%s)
                RETURNING id, title, done
                """,
                (title,),
            ).fetchone()
        return dict(row)

    def update(self, task_id: int, title: str | None, done: bool | None) -> dict | None:
        """Partially update a task; return the updated row or None."""
        with self._connect() as db:
            # First read the current row so we can preserve untouched fields.
            row = db.execute(
                "SELECT id, title, done FROM tasks WHERE id = %s", (task_id,)
            ).fetchone()
            if row is None:
                return None

            new_title = title if title is not None else row["title"]
            new_done = done if done is not None else row["done"]

            db.execute(
                """
                UPDATE tasks SET title = %s, done = %s WHERE id = %s
                RETURNING id, title, done
                """,
                (new_title, new_done, task_id),
            )
            row = db.execute(
                "SELECT id, title, done FROM tasks WHERE id = %s", (task_id,)
            ).fetchone()
        return dict(row)

    def delete(self, task_id: int) -> bool:
        """Delete a task; return True if a row was removed."""
        with self._connect() as db:
            cursor = db.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
        return cursor.rowcount > 0
