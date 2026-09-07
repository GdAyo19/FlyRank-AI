# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Task API — image for the FastAPI + SQLite app defined in appd.py.
#
#   docker build -t task-api .            # build the image
#   docker run -p 8000:8000 task-api      # run it (http://localhost:8000/docs)
#
# The app keeps tasks in a single SQLite file (tasks.db), so it doesn't need
# a database service like Postgres — a simple named volume is enough to make
# the data survive container restarts (see docker-compose.yml).
# ---------------------------------------------------------------------------

# python:3.12-slim matches the Python version used during local development
# while keeping the image small (no compilers or GUI libraries).
FROM python:3.12-slim

# Tell Python not to buffer its output. Without this, `docker logs` would
# only show logs once the buffer flushes, which is confusing when debugging.
ENV PYTHONUNBUFFERED=1

# Create a dedicated, unprivileged user. Containers should never run as
# root: if the app is ever exploited, the attacker stays limited to this
# low-privilege user instead of owning the whole container.
RUN useradd --create-home appuser

# Everything lives under /app inside the container.
WORKDIR /app

# requirements.txt is copied BEFORE the code on purpose. Docker caches each
# step of the build, so as long as this file is unchanged the expensive
# `pip install` layer is reused and rebuilds only re-copy the code (fast).
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Folder that will be mounted as a named volume by docker-compose. We create
# it and hand it to appuser BEFORE the volume attaches, so the volume
# inherits appuser's ownership and the app can write tasks.db inside it.
RUN mkdir -p /app/data && chown appuser:appuser /app/data

# Copy the rest of the project into the image. appd.py is the only module
# needed at runtime, but copying the whole folder keeps the image reusable.
COPY . .

# Drop privileges now that all setup is done.
USER appuser

# Document the port the API listens on. This is informational only — the
# actual mapping to the host happens in `docker run -p` or docker-compose.
EXPOSE 8000

# Start the FastAPI app. "appd:app" means: import appd.py, use the `app`
# object. --host 0.0.0.0 makes it reachable from outside the container.
CMD ["uvicorn", "appd:app", "--host", "0.0.0.0", "--port", "8000"]
