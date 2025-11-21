import threading
import time
import typer
import httpx
from fastapi import FastAPI, BackgroundTasks
from contextlib import asynccontextmanager
from app.command.process_command import process_next_task

# Lock to ensure only one processing job runs at a time
processing_lock = threading.Lock()

def safe_run_process():
    """
    Runs the process command safely.
    Loops processing tasks until no more tasks are available.
    """
    # Try to acquire lock without blocking. If locked, it means it's already running.
    if processing_lock.acquire(blocking=False):
        try:
            while True:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting processing check...")
                processed = False
                try:
                    processed = process_next_task()
                except Exception as e:
                    print(f"Error running process: {e}")
                
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Processing check finished. Processed: {processed}")
                
                if not processed:
                    break
        finally:
            processing_lock.release()
    else:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Worker is busy, skipping check.")

def periodic_checker():
    """
    Background thread that runs the check every 30 seconds.
    """
    while True:
        safe_run_process()
        time.sleep(30)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the background thread on startup
    print("Starting periodic checker thread...")
    thread = threading.Thread(target=periodic_checker, daemon=True)
    thread.start()
    yield
    # Cleanup if needed

app = FastAPI(lifespan=lifespan)

@app.post("/trigger")
async def trigger_processing(background_tasks: BackgroundTasks):
    """
    Endpoint to trigger immediate processing.
    """
    print("Received trigger signal.")
    background_tasks.add_task(safe_run_process)
    return {"message": "Processing triggered"}

@app.get("/health")
def health():
    return {"status": "ok"}
