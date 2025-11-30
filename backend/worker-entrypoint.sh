#!/bin/bash

export YOLO_CONFIG_DIR=${YOLO_CONFIG_DIR:-/tmp/Ultralytics}
export MPLCONFIGDIR=${MPLCONFIGDIR:-/tmp/matplotlib}

mkdir -p "$YOLO_CONFIG_DIR" "$MPLCONFIGDIR"

# Wait for backend-api with a maximum of 10 attempts
echo "Waiting for backend-api..."
for i in {1..10}; do
  if curl -f http://backend-api:8000/health; then
    echo "Backend is ready!"
    break
  fi
  echo "Backend not ready yet, attempt $i/10..."
  sleep 2
done

# If the loop ended without success, exit with error
if ! curl -f http://backend-api:8000/health; then
  echo "Backend-api not ready after 10 attempts, exiting."
  exit 1
fi

# Start the FastAPI app with Uvicorn
echo "Starting inference worker service..."
exec uvicorn app.worker_service:app --host 0.0.0.0 --port 8001
