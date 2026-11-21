"""
Worker de inferencia: toma trabajos de la cola y los procesa de a uno.

    PENDING ──claim_next()──► PROCESSING ──► DONE | FAILED

Llama a `TrafficAnalyzer.process_video(...)` (o a cualquier objeto con la misma
firma) y va guardando el progreso con el `progress_callback` de la librería.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Protocol

from .config import ServiceSettings
from .jobs import Job
from .store import JobStore

logger = logging.getLogger("siatlib.service")

RESULT_FILENAME = "result.json"
VIDEO_FILENAME = "video.mp4"


class Analyzer(Protocol):
    """Lo mínimo que el worker necesita de un analizador (TrafficAnalyzer lo cumple)."""

    def process_video(self, video_path, zones, output_video_path=None, max_frames=None,
                      progress_callback=None, imgsz=None, **kwargs) -> Any: ...


AnalyzerFactory = Callable[[Path], Analyzer]


def default_analyzer_factory(settings: ServiceSettings) -> AnalyzerFactory:
    """Crea TrafficAnalyzer reales (importa ultralytics recién al primer uso)."""

    def factory(model_path: Path) -> Analyzer:
        from ..analyzer import TrafficAnalyzer

        return TrafficAnalyzer(model_path, tracker_config=settings.tracker_config, device=settings.device)

    return factory


class Worker:
    def __init__(
        self,
        store: JobStore,
        settings: ServiceSettings,
        analyzer_factory: Optional[AnalyzerFactory] = None,
    ):
        self.store = store
        self.settings = settings
        self._factory = analyzer_factory or default_analyzer_factory(settings)
        # Un analizador por modelo: cargar YOLO es caro, se reutiliza entre trabajos.
        self._analyzers: Dict[Path, Analyzer] = {}
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.current_job_id: Optional[str] = None

    # --- Ciclo de vida -------------------------------------------------------- #

    def start(self) -> None:
        """Arranca el hilo del worker. Antes, re-encola lo que quedó a medias."""
        requeued = self.store.requeue_interrupted()
        if requeued:
            logger.warning("Se re-encolaron %d trabajos interrumpidos.", requeued)
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="siat-worker", daemon=True)
        self._thread.start()

    def stop(self, timeout: Optional[float] = None) -> None:
        """Pide que el worker termine al finalizar el trabajo en curso."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout)

    @property
    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _loop(self) -> None:
        while not self._stop.is_set():
            if not self.run_once():
                self._stop.wait(self.settings.poll_interval)

    # --- Procesamiento -------------------------------------------------------- #

    def run_once(self) -> bool:
        """Procesa el próximo trabajo pendiente. Devuelve False si la cola estaba vacía."""
        job = self.store.claim_next()
        if job is None:
            return False
        self.current_job_id = job.id
        try:
            self._process(job)
            self.store.mark_done(job.id)
            logger.info("Trabajo %s terminado.", job.id)
        except Exception as e:
            logger.error("Trabajo %s falló: %s\n%s", job.id, e, traceback.format_exc())
            self.store.mark_failed(job.id, f"{type(e).__name__}: {e}")
        finally:
            self.current_job_id = None
        return True

    def _process(self, job: Job) -> None:
        req = job.request
        video_path = self.settings.input_dir / req.video
        if not video_path.is_file():
            raise FileNotFoundError(f"No existe el video '{req.video}' en {self.settings.input_dir}.")

        model_path = self.settings.models_dir / (req.model or self.settings.default_model)
        if not model_path.is_file():
            raise FileNotFoundError(f"No existe el modelo '{model_path.name}' en {self.settings.models_dir}.")

        out_dir = self.settings.output_dir / job.id
        out_dir.mkdir(parents=True, exist_ok=True)
        out_video = out_dir / VIDEO_FILENAME if req.options.render_video else None

        logger.info("Procesando trabajo %s (video=%s, modelo=%s).", job.id, req.video, model_path.name)
        analysis = self._analyzer(model_path).process_video(
            video_path=str(video_path),
            zones=req.zone_definitions(),
            output_video_path=str(out_video) if out_video else None,
            max_frames=req.options.max_frames,
            imgsz=req.options.imgsz,
            progress_callback=self._progress_reporter(job.id),
        )

        if getattr(analysis, "total_frames_processed", 1) == 0:
            raise RuntimeError(f"No se pudo leer ningún frame del video '{req.video}'.")

        result = {
            "job_id": job.id,
            "metadata": req.metadata,
            "video": f"{job.id}/{VIDEO_FILENAME}" if out_video else None,
            **analysis.to_dict(),
        }
        # La ruta interna del contenedor no le sirve al cliente; se expone `video`.
        result.pop("output_video_path", None)
        _write_json_atomic(out_dir / RESULT_FILENAME, result)

    def _analyzer(self, model_path: Path) -> Analyzer:
        if model_path not in self._analyzers:
            self._analyzers[model_path] = self._factory(model_path)
        return self._analyzers[model_path]

    def _progress_reporter(self, job_id: str, min_interval: float = 0.5):
        """Callback para la librería: guarda el % sin escribir en la base en cada frame."""
        state = {"last_t": 0.0, "last_pct": -1.0}

        def report(frame: int, total: int, fps: float) -> None:
            if not total or total <= 0:
                return
            pct = min(100.0, frame * 100.0 / total)
            now = time.monotonic()
            if pct - state["last_pct"] >= 1.0 or now - state["last_t"] >= min_interval:
                try:
                    self.store.update_progress(job_id, pct)
                except Exception:  # El progreso nunca debe tirar abajo el procesamiento.
                    logger.exception("No se pudo guardar el progreso de %s.", job_id)
                state["last_t"], state["last_pct"] = now, pct

        return report


def _json_default(obj: Any) -> Any:
    """Convierte tipos de numpy/sets a JSON."""
    if hasattr(obj, "tolist"):
        return obj.tolist()
    if hasattr(obj, "item"):
        return obj.item()
    if isinstance(obj, (set, frozenset)):
        return sorted(obj)
    raise TypeError(f"Tipo no serializable: {type(obj).__name__}")


def _write_json_atomic(path: Path, data: Dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=_json_default)
    tmp.replace(path)
