# syntax=docker/dockerfile:1

# Use a slim Python base image
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# System dependencies
# - libmediainfo/libzen: required by pymediainfo
# - libgl1, libglib2.0-0: required by OpenCV (cv2)
# - curl: optional, useful for basic diagnostics
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    libmediainfo0v5 libzen0v5 curl \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first for better layer caching
COPY app/requirements_test.txt ./
RUN pip install --upgrade pip \
    && pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu \
    && pip install -r requirements_test.txt

# Copy application code and entrypoint scripts
COPY app/ ./app/
COPY worker-entrypoint.sh ./worker-entrypoint.sh
COPY api-entrypoint.sh ./api-entrypoint.sh

# Make scripts executable and set ownership
RUN chmod +x ./worker-entrypoint.sh ./api-entrypoint.sh \
    && chown -R www-data:www-data /app

EXPOSE 8000

USER www-data

# Default command (can be overridden by docker-compose)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
