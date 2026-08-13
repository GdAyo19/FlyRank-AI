-- Schema for the Task API (Postgres).
-- Mounted into the db container's /docker-entrypoint-initdb.d, so it runs
-- automatically the first time the volume is created. It is idempotent, so it
-- is also safe to run by hand via `psql -f db/init.sql`.

CREATE TABLE IF NOT EXISTS tasks (
    id    SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    done  BOOLEAN NOT NULL DEFAULT FALSE
);
