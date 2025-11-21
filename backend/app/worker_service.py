import threading
import time
import typer
import httpx
from fastapi import FastAPI, BackgroundTasks
from contextlib import asynccontextmanager
from app.command.process_command import run_process

# Lock to ensure only one processing job runs at a time
processing_lock = threading.Lock()

def safe_run_process():
    """
    Runs the process command safely, catching SystemExit/typer.Exit
    and ensuring only one instance runs at a time.
    """
    # Try to acquire lock without blocking. If locked, it means it's already running.
    if processing_lock.acquire(blocking=False):
        try:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting processing check...")
            try:
                run_process()
            except (SystemExit, typer.Exit):
                # Typer raises Exit to signal end of command. This is expected.
                pass
            except Exception as e:
                print(f"Error running process: {e}")
        finally:
            processing_lock.release()
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Processing check finished.")
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
