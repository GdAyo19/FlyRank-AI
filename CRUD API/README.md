# Task API

A simple CRUD API for managing a to-do list, built with **Python**, **FastAPI**, and **Postgres**.

**Persistence layer:** Postgres running in Docker (v3). Data lives in a named
Docker volume, so tasks survive both app restarts **and** container rebuilds.
A SQLite backend is still included as a server-less fallback.

## Architecture: one file to swap storage

The app never talks to a database directly — it talks to a `TaskRepository`
(`repositories/base.py`). SQLite and Postgres both implement that interface:

```
CRUD API/
├── app.py                          # FastAPI routes (never changed between storage swaps)
├── repositories/
│   ├── base.py                     # TaskRepository interface
│   ├── sqlite_repository.py        # v2 local backend
│   └── postgres_repository.py      # v3 production backend
├── db/
│   └── init.sql                    # Postgres schema (auto-run on first db boot)
├── Dockerfile                      # App image
├── docker-compose.yml              # App + Postgres, one command
├── requirements.txt
├── .env.example                    # Committed template for local config
└── .env                            # Real config (gitignored, never committed)
```

Switching storage is literally a one-line change in `.env`
(`DATABASE_URL=postgresql://…` vs `DATABASE_URL=sqlite:///tasks.db`).
The service and routes don't change at all.

## Quick Start (Postgres + app in Docker)

```bash
cp .env.example .env        # edit credentials if you like
docker compose up --build   # starts db + app together
```

- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- Postgres: localhost:5432

Stop the stack with `docker compose down` (add `-v` to also delete the data volume).

## Run the app locally without Docker

```bash
pip install -r requirements.txt
uvicorn app:app --reload
```

With the default `.env` this expects a Postgres on `localhost:5432`. To use the
server-less fallback instead, set `DATABASE_URL=sqlite:///tasks.db`.

## Configuration

| Variable           | Purpose                                   |
|--------------------|-------------------------------------------|
| `POSTGRES_USER`    | Database user (db container + app)        |
| `POSTGRES_PASSWORD`| Database password (db container + app)    |
| `POSTGRES_DB`      | Database name (db container + app)        |
| `DATABASE_URL`     | Where the app connects; `postgresql://…` or `sqlite:///…` |

`.env.example` is committed; `.env` is gitignored. Never commit real credentials.

## Endpoints

| Method | Path        | Description    |
|--------|-------------|----------------|
| GET    | `/`         | API info       |
| GET    | `/health`   | Health check   |
| GET    | `/tasks`    | List all tasks |
| GET    | `/tasks/{id}`| Get a task    |
| POST   | `/tasks`    | Create a task  |
| PUT    | `/tasks/{id}`| Update a task |
| DELETE | `/tasks/{id}`| Delete a task |

## Proving persistence

```bash
# 1. Create a task
curl -X POST http://localhost:8000/tasks -H 'Content-Type: application/json' -d '{"title": "survives a restart"}'

# 2. Restart the whole stack (app container AND database container)
docker compose down && docker compose up --build

# 3. The row is still there — data is on the named volume, not in memory
curl http://localhost:8000/tasks
```

The API surface is identical across all versions (in-memory v1 → SQLite v2 →
Postgres v3). Only the storage layer changed.
