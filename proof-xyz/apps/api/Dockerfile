# Production image for the proof.xyz / DevReel FastAPI backend.
# Portable across Render, Railway, Fly.io, or any Docker host.
FROM python:3.13-slim

# No .pyc files, unbuffered stdout so logs stream to the platform.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install deps first so this layer is cached when only app code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code.
COPY app ./app

# Run as an unprivileged user: a compromised process can't modify the image.
# /app stays writable for the SQLite fallback file.
RUN useradd --create-home --uid 10001 appuser && chown -R appuser /app
USER appuser

# The platform injects $PORT (Render/Railway/Fly). Default to 8000 locally.
ENV PORT=8000
EXPOSE 8000

# Production server: no --reload. The app is IO-bound (awaits GitHub + the
# LLM), so one async worker already serves many requests concurrently.
# Uvicorn reads WEB_CONCURRENCY for the worker count (default 1). Only raise it,
# or run several instances behind a load balancer, with REDIS_URL set (shared
# rate limits/locks) and Postgres (SQLite can't be shared). Shell form so $PORT expands.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
