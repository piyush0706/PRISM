# ── Stage 1: builder ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install dependencies into a separate layer for caching
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY main.py .

# Cloud Run injects $PORT; fall back to 8080 locally
ENV PORT=8080

EXPOSE 8080

# Use shell form so $PORT is expanded at container start
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
