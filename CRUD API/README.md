# Task API — Auth, Login & Protect

A secure REST API built with **Python** and **FastAPI** that manages a to-do list
and protects its routes with **Supabase Auth**.

- **Identity Provider:** Supabase issues and verifies the JWTs for us.
- **Swagger UI:** interactive docs at `http://localhost:8000/docs` — the
  protected routes show a padlock you can unlock with your Bearer token.
- **Persistence:** SQLite (`tasks.db`) for tasks; user accounts live in Supabase.

## How it works

A client signs up / logs in directly with Supabase, which returns a JWT
(Access Token). The client then sends that token in an
`Authorization: Bearer <token>` header on every protected request. FastAPI
verifies the token with Supabase before the route handler runs.

## Setup

### 1. Create a Supabase project

1. Create a free account at [supabase.com](https://supabase.com).
2. Spin up a new project.
3. In the dashboard go to **Project Settings -> API** and copy your
   **Project URL** and **Anon/Public Key**.

### 2. Local environment variables

Copy the example env file and fill in your own values (never commit the real one):

```bash
cp .env.example .env
```

`.env` should look like this:

```
SUPABASE_URL=your_project_url
SUPABASE_KEY=your_anon_key
PORT=8000
```

`.env` is already listed in `.gitignore`, so your keys stay off GitHub.

### 3. Install and run

```bash
pip install -r requirements.txt
uvicorn appd:app --host 0.0.0.0 --port 8000
```

Your server starts and connects to Supabase, then serves:

- Swagger UI: http://localhost:8000/docs
- API root: http://localhost:8000/

## Quick test

```bash
# Public route — no token needed
curl http://localhost:8000/public/info

# Protected route — no token, gets 401
curl http://localhost:8000/protected/profile

# Sign up
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# Log in and grab the access_token
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# Use the token on a protected route
curl http://localhost:8000/protected/profile \
  -H "Authorization: Bearer <your_access_token>"
```

You can also use the **Authorize** padlock in Swagger UI: paste your token once
and every protected route unlocks for testing.

## API reference

| Method | Path                    | Auth required | Description                              |
|--------|-------------------------|---------------|------------------------------------------|
| POST   | `/auth/signup`          | No            | Create a new user (201 on success)       |
| POST   | `/auth/login`           | No            | Authenticate & return access/refresh JWT |
| POST   | `/auth/logout`          | Yes           | Terminate the session (204)              |
| GET    | `/public/info`          | No            | Public info for everyone                 |
| GET    | `/protected/profile`    | Yes           | Logged-in user's profile data            |
| GET    | `/protected/dashboard`  | Yes           | Example of a second protected route      |
| GET    | `/`                     | No            | API info                                 |
| GET    | `/health`               | No            | Health check                             |
| GET    | `/tasks`                | No            | List all tasks                           |
| GET    | `/tasks/{id}`           | No            | Get a single task                        |
| POST   | `/tasks`                | No            | Create a task (201)                      |
| PUT    | `/tasks/{id}`           | No            | Update a task                            |
| DELETE | `/tasks/{id}`           | No            | Delete a task (204)                      |

## Status codes

| Code | Meaning                                      |
|------|----------------------------------------------|
| 201  | Created (signup / task created)              |
| 200  | OK (successful login / read)                 |
| 204  | No Content (logout / delete)                 |
| 400  | Bad Request (missing email or password)      |
| 401  | Unauthorized (missing, invalid or expired token) |
| 404  | Not Found (task doesn't exist)               |

## Swagger UI

![Swagger UI](docs/swagger-screenshot.png)

> TODO: replace `docs/swagger-screenshot.png` with a screenshot of your own
> `/docs` page showing the padlock next to the protected routes.

## Project structure

```
.
├── appd.py            # FastAPI app: Supabase client, auth, and CRUD routes
├── requirements.txt   # Python dependencies
├── .env.example       # Template for your local env vars
├── .gitignore         # Keeps .env and secrets out of git
└── README.md
```