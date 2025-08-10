# syntax=docker/dockerfile:1

# Use a slim Python base image
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# System dependencies
# - libmediainfo/libzen: required by pymediainfo
# - curl: optional, useful for basic diagnostics
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    libmediainfo0v5 libzen0v5 curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN addgroup --system app && adduser --system --ingroup app app

WORKDIR /app

# Install Python dependencies first for better layer caching
COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Copy application code
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

EXPOSE 8000

USER app

# Default command (can be overridden by docker-compose)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
