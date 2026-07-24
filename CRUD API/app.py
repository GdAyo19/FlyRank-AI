from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3  # Built-in module; no pip install needed.

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

DB_PATH = "tasks.db"  # SQLite file that persists tasks to disk.


def get_db() -> sqlite3.Connection:
    """Return a connection to the SQLite database (autocommit mode)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us access columns by name
    conn.execute("PRAGMA journal_mode=WAL")  # better concurrent-read performance
    return conn


def init_db() -> None:
    """Create the tasks table if it doesn't already exist."""
    with get_db() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id    INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT    NOT NULL,
                done  INTEGER NOT NULL DEFAULT 0   -- SQLite has no bool; 0 = False, 1 = True
            )
            """
        )

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="Task API", description="A simple CRUD API to manage a to-do list.", version="2.0")


@app.on_event("startup")
def on_startup() -> None:
    """Ensure the database and table exist when the server starts."""
    init_db()


# ---------------------------------------------------------------------------
# Pydantic models (request bodies)
# ---------------------------------------------------------------------------


class TaskCreate(BaseModel):
    title: str


class TaskUpdate(BaseModel):
    title: str | None = None
    done: bool | None = None


# ---------------------------------------------------------------------------
# Helper: convert a sqlite3.Row to the dict shape clients expect
# ---------------------------------------------------------------------------


def _row_to_task(row: sqlite3.Row) -> dict:
    """Map a database row to the JSON-safe dict returned by every endpoint."""
    return {
        "id": row["id"],
        "title": row["title"],
        "done": bool(row["done"]),  # convert 0/1 integer to Python bool
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/")
def root():
    return {"name": "Task API", "version": "2.0"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/tasks")
def list_tasks():
    """Return every task in the database."""
    with get_db() as db:
        rows = db.execute("SELECT id, title, done FROM tasks ORDER BY id").fetchall()
    return [_row_to_task(r) for r in rows]


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    """Return a single task by its primary-key id, or 404."""
    with get_db() as db:
        row = db.execute(
            "SELECT id, title, done FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return _row_to_task(row)


@app.post("/tasks", status_code=201)
def create_task(body: TaskCreate):
    """Insert a new task and return it with the auto-generated id."""
    with get_db() as db:
        cursor = db.execute(
            "INSERT INTO tasks (title, done) VALUES (?, 0)", (body.title,)
        )
        # Read back the row we just inserted so the caller gets a complete object.
        row = db.execute(
            "SELECT id, title, done FROM tasks WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
    return _row_to_task(row)


@app.put("/tasks/{task_id}")
def update_task(task_id: int, body: TaskUpdate):
    """Partially or fully update a task; return the updated row or 404."""
    with get_db() as db:
        row = db.execute(
            "SELECT id, title, done FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Task not found")

        new_title = body.title if body.title is not None else row["title"]
        new_done = int(body.done) if body.done is not None else row["done"]

        db.execute(
            "UPDATE tasks SET title = ?, done = ? WHERE id = ?",
            (new_title, new_done, task_id),
        )
        row = db.execute(
            "SELECT id, title, done FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
    return _row_to_task(row)


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    """Remove a task from the database; 404 if it doesn't exist."""
    with get_db() as db:
        cursor = db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Task not found")
    return None  # 204 No Content — no body sent to client