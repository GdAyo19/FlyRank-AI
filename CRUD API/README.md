# Task API

A simple CRUD API for managing a to-do list, built with **Python** and **FastAPI**.

**Persistence layer:** SQLite (`tasks.db`) — data survives server restarts.  
No external database server needed; everything lives in a single file on disk.

## Quick Start

```bash
pip install fastapi uvicorn
uvicorn app:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000/docs for Swagger UI.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | API info |
| GET | `/health` | Health check |
| GET | `/tasks` | List all tasks |
| GET | `/tasks/{id}` | Get a task |
| POST | `/tasks` | Create a task |
| PUT | `/tasks/{id}` | Update a task |
| DELETE | `/tasks/{id}` | Delete a task |

The API surface is identical to the in-memory v1. Only the storage layer changed.
