# Task API

A simple CRUD API for managing a to-do list, built with **Python** and **FastAPI**.

Data is stored in memory (a Python list) — restarting the server resets everything. No database required.

## Quick Start

```bash
# 1. Install dependencies
pip install fastapi uvicorn

# 2. Start the server
uvicorn app:app --host 0.0.0.0 --port 8000

# 3. Open in browser
#    http://localhost:8000        → API info
#    http://localhost:8000/docs   → Swagger UI (interactive docs)
```

## Endpoints

| Method | Path              | Status Codes               | Description                    |
|--------|-------------------|----------------------------|--------------------------------|
| GET    | `/`               | 200                        | API info (name, version)       |
| GET    | `/health`         | 200                        | Health check                   |
| GET    | `/tasks`          | 200                        | List all tasks                 |
| GET    | `/tasks/{id}`     | 200, 404                   | Get a single task by ID        |
| POST   | `/tasks`          | 201, 400                   | Create a new task              |
| PUT    | `/tasks/{id}`     | 200, 400, 404              | Update a task                  |
| DELETE | `/tasks/{id}`     | 204, 404                   | Delete a task                  |
| GET    | `/stats`          | 200                        | Task statistics (extra)        |
| POST   | `/reset`          | 200                        | Reset to example tasks (extra) |

### Query parameters for `GET /tasks`

- `?done=true` — filter by completion status
- `?search=word` — search titles (case-insensitive)
- `?limit=2&offset=2` — pagination (skip N, return M)

## Example curl commands

```bash
# List all tasks
curl -i http://localhost:8000/tasks

# Get task with ID 1
curl -i http://localhost:8000/tasks/1

# Get task with ID 99 (→ 404)
curl -i http://localhost:8000/tasks/99

# Create a task (→ 201)
curl -i -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"Buy milk"}'

# Create with empty title (→ 400)
curl -i -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":""}'

# Update a task
curl -i -X PUT http://localhost:8000/tasks/4 \
  -H "Content-Type: application/json" \
  -d '{"done":true}'

# Delete a task (→ 204)
curl -i -X DELETE http://localhost:8000/tasks/4
```

## Screenshot

![Swagger UI](screenshot.png)

Add a screenshot of http://localhost:8000/docs here.

## Mortality Experiment

Restart the server and run `GET /tasks` — you'll see only the 3 original example tasks. Any tasks you created are gone. This happens because the data lives in a Python list in memory. When the process stops, the list is destroyed. A database (coming in Week 3) would persist data across restarts.
