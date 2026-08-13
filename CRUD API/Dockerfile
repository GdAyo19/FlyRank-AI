# Task API — app image
FROM python:3.12-slim

WORKDIR /app

# Install dependencies first for better Docker layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code (repositories + app).
COPY app.py .
COPY repositories ./repositories

# FastAPI + uvicorn standard entrypoint.
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]