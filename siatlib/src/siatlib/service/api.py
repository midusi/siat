"""
API HTTP del servicio de inferencia (contrato: docs/SIATLIB_SERVICE_API.md).

Requiere el extra `service`:  pip install "siatlib[service]"
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Literal, Optional

try:
    from fastapi import FastAPI, HTTPException, Query
    from fastapi.responses import FileResponse
    from pydantic import BaseModel, Field
except ImportError as e:  # pragma: no cover
    raise ImportError(
        "La API del servicio necesita FastAPI. Instalá el extra: pip install 'siatlib[service]'"
    ) from e

from .config import ServiceSettings
from .jobs import InvalidJobRequest, InvalidTransition, JobRequest, JobStatus
from .store import JobNotFound, JobStore
from .worker import RESULT_FILENAME, VIDEO_FILENAME, Worker

logger = logging.getLogger("siatlib.service")

API_VERSION = "v1"


# --- Esquemas (solo para validar tipos y documentar en /docs) ----------------- #


class ZoneIn(BaseModel):
    name: str = Field(..., examples=["Entrada Sur"])
    type: Literal["entry", "exit", "excluded"]
    polygon: List[List[int]] = Field(..., examples=[[[544, 913], [617, 1005], [824, 939], [705, 839]]])


class OptionsIn(BaseModel):
    max_frames: Optional[int] = None
    imgsz: Optional[int] = None
    render_video: bool = True


class JobRequestIn(BaseModel):
    video: str = Field(..., description="Ruta relativa a /data/input/", examples=["rotonda_1/video.mp4"])
    zones: List[ZoneIn]
    model: Optional[str] = Field(None, description="Archivo dentro de /models/", examples=["model-v5.pt"])
    options: OptionsIn = Field(default_factory=OptionsIn)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class JobOut(BaseModel):
    id: str
    status: JobStatus
    progress: float
    error: Optional[str]
    created_at: str
    started_at: Optional[str]
    finished_at: Optional[str]
    request: Dict[str, Any]
    metadata: Dict[str, Any]


# --- App ------------------------------------------------------------------------ #


def create_app(
    settings: Optional[ServiceSettings] = None,
    store: Optional[JobStore] = None,
    worker: Optional[Worker] = None,
    start_worker: bool = True,
) -> FastAPI:
    settings = settings or ServiceSettings.from_env()
    settings.ensure_dirs()
    store = store or JobStore(settings.db_path)
    worker = worker or Worker(store, settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if start_worker:
            worker.start()
        yield
        if start_worker:
            worker.stop(timeout=5)

    app = FastAPI(
        title="SIAT — servicio de inferencia",
        version=API_VERSION,
        description="Cola de procesamiento de videos de tránsito con siatlib. "
        "Contrato: docs/SIATLIB_SERVICE_API.md",
        lifespan=lifespan,
    )
    app.state.settings, app.state.store, app.state.worker = settings, store, worker

    def get_job_or_404(job_id: str):
        try:
            return store.get(job_id)
        except JobNotFound as e:
            raise HTTPException(404, str(e))

    def require_done(job_id: str):
        job = get_job_or_404(job_id)
        if job.status != JobStatus.DONE:
            raise HTTPException(409, f"El trabajo está en {job.status.value}; los resultados están disponibles en DONE.")
        return job

    @app.post("/jobs", status_code=202, response_model=JobOut, summary="Encolar un trabajo")
    def create_job(body: JobRequestIn):
        try:
            request = JobRequest.from_dict(body.model_dump())
        except InvalidJobRequest as e:
            raise HTTPException(422, str(e))
        # Fallar rápido si el archivo no está, en lugar de encolarlo y que falle después.
        if not (settings.input_dir / request.video).is_file():
            raise HTTPException(422, f"No existe el video '{request.video}' en {settings.input_dir}.")
        model = request.model or settings.default_model
        if not (settings.models_dir / model).is_file():
            raise HTTPException(422, f"No existe el modelo '{model}' en {settings.models_dir}.")
        job = store.create(request)
        logger.info("Trabajo %s encolado (video=%s).", job.id, request.video)
        return job.to_dict()

    @app.get("/jobs", response_model=List[JobOut], summary="Listar trabajos")
    def list_jobs(status: Optional[JobStatus] = None, limit: int = Query(50, ge=1, le=500)):
        return [j.to_dict() for j in store.list(status=status, limit=limit)]

    @app.get("/jobs/{job_id}", response_model=JobOut, summary="Estado y progreso")
    def get_job(job_id: str):
        return get_job_or_404(job_id).to_dict()

    @app.get("/jobs/{job_id}/result", summary="Resultados (JSON)")
    def get_result(job_id: str):
        require_done(job_id)
        path = settings.output_dir / job_id / RESULT_FILENAME
        if not path.is_file():
            raise HTTPException(404, "El trabajo terminó pero no se encontró result.json.")
        return FileResponse(path, media_type="application/json")

    @app.get("/jobs/{job_id}/video", summary="Video renderizado")
    def get_video(job_id: str):
        job = require_done(job_id)
        path = settings.output_dir / job_id / VIDEO_FILENAME
        if not job.request.options.render_video or not path.is_file():
            raise HTTPException(404, "Este trabajo no tiene video renderizado.")
        return FileResponse(path, media_type="video/mp4", filename=f"{job_id}.mp4")

    @app.delete("/jobs/{job_id}", response_model=JobOut, summary="Cancelar un trabajo pendiente")
    def cancel_job(job_id: str):
        get_job_or_404(job_id)
        try:
            return store.cancel(job_id).to_dict()
        except InvalidTransition as e:
            raise HTTPException(409, f"Solo se pueden cancelar trabajos PENDING ({e}).")

    @app.get("/health", summary="Estado del servicio")
    def health():
        return {
            "status": "ok",
            "version": API_VERSION,
            "worker_alive": worker.is_alive,
            "current_job": worker.current_job_id,
            "device": _device_info(settings.device),
            "default_model": settings.default_model,
            "default_model_found": (settings.models_dir / settings.default_model).is_file(),
            "queue": store.counts(),
        }

    return app


def _device_info(preferred: str) -> Dict[str, Any]:
    try:
        import torch

        cuda = torch.cuda.is_available()
        return {
            "configured": preferred,
            "cuda_available": cuda,
            "gpu": torch.cuda.get_device_name(0) if cuda else None,
        }
    except Exception as e:  # pragma: no cover
        return {"configured": preferred, "cuda_available": False, "error": str(e)}
