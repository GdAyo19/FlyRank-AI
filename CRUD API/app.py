from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
from dotenv import load_dotenv

from repositories import TaskRepository, SqliteTaskRepository, PostgresTaskRepository

# Load DATABASE_URL (and friends) from the .env file, if present. Environment
# variables already set (e.g. injected by docker-compose) always win.
load_dotenv()


# ---------------------------------------------------------------------------
# Repository factory: decide which storage backend to use.
# Swapping storage = changing one line in .env. The routes below never change.
# ---------------------------------------------------------------------------

def build_repository() -> TaskRepository:
    """Pick a TaskRepository based on the DATABASE_URL in the environment."""
    db_url = os.getenv("DATABASE_URL", "sqlite:///tasks.db")
    if db_url.startswith("postgresql"):
        return PostgresTaskRepository(db_url)   # Dockerized Postgres (default)
    if db_url.startswith("sqlite"):
        path = db_url.split("///")[-1] or "tasks.db"
        return SqliteTaskRepository(path)       # Local fallback, no server needed
    raise ValueError(f"Unsupported DATABASE_URL scheme: {db_url!r}")


repo = build_repository()


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="Task API", description="A simple CRUD API to manage a to-do list.", version="3.0")


@app.on_event("startup")
def on_startup() -> None:
    """Ensure the database and table exist when the server starts."""
    repo.init()


# ---------------------------------------------------------------------------
# Pydantic models (request bodies)
# ---------------------------------------------------------------------------


class TaskCreate(BaseModel):
    title: str


class TaskUpdate(BaseModel):
    title: str | None = None
    done: bool | None = None


# ---------------------------------------------------------------------------
# Endpoints — identical API surface to v1/v2; only the storage backend changed.
# ---------------------------------------------------------------------------


@app.get("/")
def root():
    return {"name": "Task API", "version": "3.0"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/tasks")
def list_tasks():
    """Return every task in the database."""
    return repo.list()


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    """Return a single task by its primary-key id, or 404."""
    task = repo.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.post("/tasks", status_code=201)
def create_task(body: TaskCreate):
    """Insert a new task and return it with the auto-generated id."""
    return repo.create(body.title)


@app.put("/tasks/{task_id}")
def update_task(task_id: int, body: TaskUpdate):
    """Partially or fully update a task; return the updated row or 404."""
    task = repo.update(task_id, body.title, body.done)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    """Remove a task from the database; 404 if it doesn't exist."""
    if not repo.delete(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    return None  # 204 No Content — no body sent to client
