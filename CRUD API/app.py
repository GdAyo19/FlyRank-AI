"""
Task API — A simple CRUD API for managing a to-do list.

Built with FastAPI. Data lives in memory (a Python list).
Swagger UI available at /docs (provided automatically by FastAPI).
"""

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# ----------------------------------------------------------------
# App setup
# ----------------------------------------------------------------
app = FastAPI(
    title="Task API",
    description="A simple CRUD API to manage a to-do list.",
    version="1.0",
)


# ----------------------------------------------------------------
# Convert FastAPI's default 422 validation errors to 400
# to match the assignment requirement
# ----------------------------------------------------------------
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return 400 instead of 422 for invalid request bodies."""
    errors = exc.errors()
    # Build a human-readable error message from the validation errors
    messages = []
    for err in errors:
        field = ".".join(str(loc) for loc in err.get("loc", []) if loc != "body")
        msg = err.get("msg", "Invalid value")
        messages.append(f"{field}: {msg}" if field else msg)
    return JSONResponse(
        status_code=400,
        content={"error": "; ".join(messages)},
    )


# ----------------------------------------------------------------
# In-memory "database" — a list of task dicts, pre-filled with examples
# ----------------------------------------------------------------
tasks = [
    {"id": 1, "title": "Buy groceries", "done": False},
    {"id": 2, "title": "Walk the dog", "done": False},
    {"id": 3, "title": "Write a CRUD API", "done": True},
]

# ID counter — starts after the pre-filled tasks so new tasks get fresh IDs
next_id = 4


# ----------------------------------------------------------------
# Pydantic models — define the shape of request/response data
# ----------------------------------------------------------------
class TaskCreate(BaseModel):
    """Shape of the JSON body when creating a task."""
    title: str = Field(..., min_length=1, description="Title of the task (required, must not be empty)")


class TaskUpdate(BaseModel):
    """Shape of the JSON body when updating a task.
    Both fields are optional — the client can send just what they want to change."""
    title: str | None = Field(None, min_length=1, description="New title")
    done: bool | None = Field(None, description="Completion status")


# ----------------------------------------------------------------
# Endpoints
# ----------------------------------------------------------------

@app.get("/")
def root():
    """Stage 1: API information endpoint."""
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks"],
    }


@app.get("/health")
def health():
    """Stage 1: Health check — used by monitoring to see if the server is alive."""
    return {"status": "ok"}


@app.get("/tasks")
def list_tasks(
    done: bool | None = Query(None, description="Filter by completion status"),
    search: str | None = Query(None, description="Search in task titles"),
    limit: int | None = Query(None, ge=1, description="Max number of tasks to return"),
    offset: int | None = Query(None, ge=0, description="Number of tasks to skip"),
):
    """Stage 2: List all tasks. Supports optional filtering, search, and pagination.

    - ?done=true   → only completed tasks
    - ?done=false  → only open tasks
    - ?search=milk → tasks whose title contains "milk" (case-insensitive)
    - ?limit=2&offset=2 → pagination: skip 2, return 2
    """
    result = tasks

    # Filter by completion status
    if done is not None:
        result = [t for t in result if t["done"] == done]

    # Search by title (case-insensitive)
    if search:
        search_lower = search.lower()
        result = [t for t in result if search_lower in t["title"].lower()]

    # Pagination (apply after filtering)
    if offset is not None:
        result = result[offset:]
    if limit is not None:
        result = result[:limit]

    return result


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    """Stage 2: Get a single task by its ID. Returns 404 if not found."""
    for task in tasks:
        if task["id"] == task_id:
            return task
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


@app.post("/tasks", status_code=201)
def create_task(body: TaskCreate):
    """Stage 3: Create a new task.

    Expects JSON like { "title": "Buy milk" }.
    Returns the created task with status 201.
    Title is required and must not be empty — otherwise 400.
    """
    global next_id
    new_task = {
        "id": next_id,
        "title": body.title,
        "done": False,
    }
    tasks.append(new_task)
    next_id += 1
    return new_task


@app.put("/tasks/{task_id}")
def update_task(task_id: int, body: TaskUpdate):
    """Stage 4: Update an existing task.

    Send any combination of { "title": "...", "done": true/false }.
    Unknown ID → 404.  Empty title → 400.
    """
    for task in tasks:
        if task["id"] == task_id:
            if body.title is not None:
                task["title"] = body.title
            if body.done is not None:
                task["done"] = body.done
            return task

    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    """Stage 4: Delete a task. Returns 204 with no body. Unknown ID → 404."""
    for i, task in enumerate(tasks):
        if task["id"] == task_id:
            tasks.pop(i)
            return  # 204 No Content — no body sent

    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


# ----------------------------------------------------------------
# Extra endpoints (optional fun features)
# ----------------------------------------------------------------

@app.get("/stats")
def stats():
    """Extra: Compute stats — total, done, and open task counts."""
    total = len(tasks)
    done_count = sum(1 for t in tasks if t["done"])
    return {"total": total, "done": done_count, "open": total - done_count}


@app.post("/reset")
def reset():
    """Extra: Restore the 3 original example tasks. Useful for demos."""
    global tasks, next_id
    tasks.clear()
    tasks.extend([
        {"id": 1, "title": "Buy groceries", "done": False},
        {"id": 2, "title": "Walk the dog", "done": False},
        {"id": 3, "title": "Write a CRUD API", "done": True},
    ])
    next_id = 4
    return {"message": "Tasks reset to defaults"}
