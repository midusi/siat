#!/bin/bash
set -e

echo "=== Backend API Initialization ==="

# Change to app directory for alembic
cd /app/app

echo "Waiting for database to be ready..."
# Retry logic for database connection
MAX_RETRIES=30
RETRY_COUNT=0
until alembic upgrade head 2>/dev/null || [ $RETRY_COUNT -eq $MAX_RETRIES ]; do
  RETRY_COUNT=$((RETRY_COUNT+1))
  echo "Database not ready yet (attempt $RETRY_COUNT/$MAX_RETRIES), waiting..."
  sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
  echo "ERROR: Could not connect to database after $MAX_RETRIES attempts"
  exit 1
fi

echo "Running database migrations..."
alembic upgrade head

echo "Migrations completed successfully!"

# Run seeds to initialize database data
echo "Running database seeds..."
python -m seeds

# Initialize MinIO bucket
echo "Initializing MinIO bucket..."
python -m init_bucket

# Return to root and start the server
cd /app

echo "Starting FastAPI server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
