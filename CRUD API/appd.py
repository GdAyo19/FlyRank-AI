from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from supabase import create_client, Client
from gotrue.errors import AuthApiError
from dotenv import load_dotenv
import os
import sqlite3  # Built-in module; no pip install needed.
import os  # used to read the TASK_DB_PATH env var so Docker can relocate the db file

# ---------------------------------------------------------------------------
# Environment & Supabase client
# ---------------------------------------------------------------------------

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "Missing SUPABASE_URL or SUPABASE_KEY. Copy .env.example to .env and fill it in."
    )

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

# The database file can be moved with the TASK_DB_PATH environment variable.
# Docker Compose uses this to point at a file inside a named volume, so tasks
# survive container restarts. When the env var is missing we fall back to a
# plain "tasks.db" in the current folder (how the app behaved before Docker).
DB_PATH = os.environ.get("TASK_DB_PATH", "tasks.db")

# SQLite won't create parent directories for us. In Docker the volume mount
# starts out empty, so make sure the folder that will hold the db exists.
_db_dir = os.path.dirname(DB_PATH)
if _db_dir:
    os.makedirs(_db_dir, exist_ok=True)


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

app = FastAPI(
    title="Task API",
    description="A simple CRUD API with Supabase Auth. "
    "Use the **Authorize** button below to paste your Bearer token for the protected routes.",
    version="3.0",
    openapi_tags=[
        {"name": "Auth", "description": "Sign up, log in and log out"},
        {"name": "Public", "description": "Open endpoints"},
        {"name": "Protected", "description": "Endpoints that need a valid Bearer token"},
        {"name": "Tasks", "description": "CRUD for tasks"},
    ],
)


@app.on_event("startup")
def on_startup() -> None:
    """Ensure the database and table exist when the server starts."""
    init_db()
    print("Server running and connected to Supabase")


# ---------------------------------------------------------------------------
# Pydantic models (request bodies)
# ---------------------------------------------------------------------------


class TaskCreate(BaseModel):
    title: str


class TaskUpdate(BaseModel):
    title: str | None = None
    done: bool | None = None


class AuthRequest(BaseModel):
    # Optional so a missing/empty field reaches our manual check and returns
    # 400, instead of Pydantic's automatic 422.
    email: str | None = None
    password: str | None = None


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
# Auth dependency (middleware): verifies the Bearer token on every call
# ---------------------------------------------------------------------------

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict:
    """Extract and verify the Bearer token, returning the logged-in user."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Access token required")
    try:
        res = supabase.auth.get_user(credentials.credentials)
        return res.user  # dict-like object with id, email, created_at, ...
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------


@app.post("/auth/signup", status_code=201, tags=["Auth"])
def signup(body: AuthRequest):
    """Register a new user with Supabase Auth."""
    if not body.email or not body.password:
        raise HTTPException(status_code=400, detail="Email and password are required")
    try:
        res = supabase.auth.sign_up({"email": body.email, "password": body.password})
    except AuthApiError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return res.user


@app.post("/auth/login", tags=["Auth"])
def login(body: AuthRequest):
    """Authenticate a user and return the JWT access + refresh tokens."""
    if not body.email or not body.password:
        raise HTTPException(status_code=400, detail="Email and password are required")
    try:
        res = supabase.auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
    except AuthApiError:
        raise HTTPException(status_code=401, detail="Invalid login credentials")
    return {
        "access_token": res.session.access_token,
        "refresh_token": res.session.refresh_token,
    }


# ---------------------------------------------------------------------------
# Public & protected endpoints
# ---------------------------------------------------------------------------


@app.get("/public/info", tags=["Public"])
def public_info():
    """Open route that needs no authentication at all."""
    return {"message": "Welcome stranger! This info is public."}


@app.post("/auth/logout", status_code=204, tags=["Auth"])
def logout(user: dict = Depends(get_current_user)):
    """Terminate the current user session (requires a valid Bearer token)."""
    try:
        supabase.auth.sign_out()
    except AuthApiError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return None  # 204 No Content — no body sent to client


@app.get("/protected/profile", tags=["Protected"])
def protected_profile(user: dict = Depends(get_current_user)):
    """Return the logged-in user's profile data (token verified)."""
    return {
        "id": user.id,
        "email": user.email,
        "created_at": user.created_at,
    }


@app.get("/protected/dashboard", tags=["Protected"])
def protected_dashboard(user: dict = Depends(get_current_user)):
    """Second protected route to prove the middleware guards any endpoint."""
    return {"message": f"Welcome back, {user.email}! This is your dashboard."}


# ---------------------------------------------------------------------------
# Task CRUD endpoints (kept from v2)
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