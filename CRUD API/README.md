# Task API

A simple CRUD API for managing a to-do list, built with **Python** and **FastAPI**.

**Persistence layer:** SQLite (`tasks.db`) — data survives server restarts.  
No external database server needed; everything lives in a single file on disk.

## Quick Start

```bash
pip install fastapi uvicorn
uvicorn appd:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000/docs for Swagger UI.

## Run with Docker

The project ships with a `Dockerfile` and a `docker-compose.yml` so you can
run the whole API in a container without installing Python locally.

```bash
# Build the image and start the container (add -d to run in the background)
docker compose up --build
```

The SQLite database is stored in a **named volume** (`task_data`), so your
tasks survive container restarts and `docker compose down`. To start over
from scratch, delete the volume too:

```bash
docker compose down -v
```

To run the bare image without Compose:

```bash
docker build -t task-api .
docker run --rm -p 8000:8000 -e TASK_DB_PATH=/app/data/tasks.db task-api
```

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `TASK_DB_PATH` | `tasks.db` | Where the SQLite file lives. Docker Compose points it at `/app/data/tasks.db` inside the volume. |

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
