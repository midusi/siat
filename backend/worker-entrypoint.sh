#!/bin/bash

export YOLO_CONFIG_DIR=${YOLO_CONFIG_DIR:-/tmp/Ultralytics}
export MPLCONFIGDIR=${MPLCONFIGDIR:-/tmp/matplotlib}

mkdir -p "$YOLO_CONFIG_DIR" "$MPLCONFIGDIR"

echo "Starting inference worker service..."

# Start the FastAPI app with Uvicorn
# This replaces the infinite loop in bash
exec uvicorn app.worker_service:app --host 0.0.0.0 --port 8001
