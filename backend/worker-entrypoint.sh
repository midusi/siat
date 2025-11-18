#!/bin/bash

echo "Starting inference worker..."
echo "Polling for tasks every 30 seconds..."

# Loop infinitely to process tasks
while true; do
  echo "[$(date)] Checking for tasks to process..."
  
  # Run the process command
  # Use || true to prevent the loop from breaking if the command fails
  python -m app.command.process_command || {
    echo "[$(date)] ERROR: Process command failed, continuing..."
  }
  
  # Wait 30 seconds before checking again
  sleep 30
done
