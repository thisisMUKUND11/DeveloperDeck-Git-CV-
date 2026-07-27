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

# The platform injects $PORT (Render/Railway/Fly). Default to 8000 locally.
ENV PORT=8000
EXPOSE 8000

# Production server: no --reload. Single async worker — the app is IO-bound
# (awaits GitHub + the LLM) so async handles concurrency, and one worker keeps
# the rate-limiter counters in one process. Shell form so $PORT expands.
# --proxy-headers: the platform terminates TLS and forwards X-Forwarded-*, so
# without it every request would look like it came from the load balancer.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'
