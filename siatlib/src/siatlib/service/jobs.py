"""
Modelo de trabajos (jobs) del servicio de inferencia: estados, transiciones y pedido.

No depende de FastAPI ni de la base de datos; se puede usar desde Python puro.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import PurePosixPath
from typing import Any, Dict, List, Optional

from ..models import ZoneDefinition, ZoneType


class JobStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    DONE = "DONE"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

    @property
    def is_final(self) -> bool:
        return self in FINAL_STATUSES


FINAL_STATUSES = frozenset({JobStatus.DONE, JobStatus.FAILED, JobStatus.CANCELLED})

# Transiciones válidas. PROCESSING -> PENDING solo ocurre al reiniciar el servicio
# (el trabajo que estaba en curso vuelve a la cola).
ALLOWED_TRANSITIONS: Dict[JobStatus, frozenset] = {
    JobStatus.PENDING: frozenset({JobStatus.PROCESSING, JobStatus.CANCELLED}),
    JobStatus.PROCESSING: frozenset({JobStatus.DONE, JobStatus.FAILED, JobStatus.PENDING}),
    JobStatus.DONE: frozenset(),
    JobStatus.FAILED: frozenset(),
    JobStatus.CANCELLED: frozenset(),
}


class InvalidTransition(Exception):
    """Se intentó pasar un trabajo a un estado no permitido desde el actual."""

    def __init__(self, job_id: str, current: JobStatus, target: JobStatus):
        super().__init__(f"El trabajo {job_id} está en {current.value} y no puede pasar a {target.value}.")
        self.job_id = job_id
        self.current = current
        self.target = target


class InvalidJobRequest(ValueError):
    """El pedido de trabajo no cumple el contrato."""


def can_transition(current: JobStatus, target: JobStatus) -> bool:
    return target in ALLOWED_TRANSITIONS[current]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_job_id() -> str:
    return uuid.uuid4().hex


# --------------------------------------------------------------------------- #
# Pedido                                                                       #
# --------------------------------------------------------------------------- #

_ZONE_TYPES = {"entry": ZoneType.ENTRY, "exit": ZoneType.EXIT, "excluded": ZoneType.EXCLUDED}


@dataclass
class ZoneSpec:
    name: str
    type: str  # "entry" | "exit" | "excluded"
    polygon: List[List[int]]

    def to_zone_definition(self) -> ZoneDefinition:
        return ZoneDefinition(
            name=self.name,
            polygon=[(int(x), int(y)) for x, y in self.polygon],
            zone_type=_ZONE_TYPES[self.type],
        )


@dataclass
class JobOptions:
    max_frames: Optional[int] = None
    imgsz: Optional[int] = None
    render_video: bool = True


@dataclass
class JobRequest:
    """Pedido de procesamiento de un video (ver docs/SIATLIB_SERVICE_API.md, sección 4)."""

    video: str
    zones: List[ZoneSpec]
    model: Optional[str] = None
    options: JobOptions = field(default_factory=JobOptions)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JobRequest":
        """Construye y valida un pedido a partir de un dict (p. ej. el JSON recibido)."""
        if not isinstance(data, dict):
            raise InvalidJobRequest("El pedido debe ser un objeto JSON.")
        try:
            zones = [
                ZoneSpec(name=z["name"], type=z["type"], polygon=[list(p) for p in z["polygon"]])
                for z in data.get("zones") or []
            ]
            options = JobOptions(**(data.get("options") or {}))
        except (KeyError, TypeError) as e:
            raise InvalidJobRequest(f"Formato inválido: {e}") from e

        req = cls(
            video=data.get("video") or "",
            zones=zones,
            model=data.get("model"),
            options=options,
            metadata=dict(data.get("metadata") or {}),
        )
        req.validate()
        return req

    def validate(self) -> None:
        if not self.video:
            raise InvalidJobRequest("Falta 'video'.")
        _check_relative_path(self.video, "video")
        if self.model is not None:
            _check_relative_path(self.model, "model")

        for z in self.zones:
            if z.type not in _ZONE_TYPES:
                raise InvalidJobRequest(f"Zona '{z.name}': tipo '{z.type}' inválido (entry, exit o excluded).")
            if not z.name:
                raise InvalidJobRequest("Todas las zonas deben tener nombre.")
            if len(z.polygon) < 3:
                raise InvalidJobRequest(f"Zona '{z.name}': el polígono necesita al menos 3 vértices.")
            if any(len(p) != 2 for p in z.polygon):
                raise InvalidJobRequest(f"Zona '{z.name}': cada vértice debe ser [x, y].")
        types = {z.type for z in self.zones}
        if "entry" not in types or "exit" not in types:
            raise InvalidJobRequest("Se necesita al menos una zona 'entry' y una 'exit'.")

        o = self.options
        if o.max_frames is not None and o.max_frames <= 0:
            raise InvalidJobRequest("'options.max_frames' debe ser positivo.")
        if o.imgsz is not None and o.imgsz <= 0:
            raise InvalidJobRequest("'options.imgsz' debe ser positivo.")

    def zone_definitions(self) -> List[ZoneDefinition]:
        return [z.to_zone_definition() for z in self.zones]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _check_relative_path(value: str, field_name: str) -> None:
    """Rechaza rutas absolutas o que intenten salir del directorio base (`..`)."""
    p = PurePosixPath(value.replace("\\", "/"))
    if p.is_absolute() or ".." in p.parts:
        raise InvalidJobRequest(f"'{field_name}' debe ser una ruta relativa sin '..'.")


# --------------------------------------------------------------------------- #
# Trabajo                                                                      #
# --------------------------------------------------------------------------- #


@dataclass
class Job:
    id: str
    status: JobStatus
    request: JobRequest
    progress: float = 0.0
    error: Optional[str] = None
    created_at: datetime = field(default_factory=utcnow)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Representación pública del trabajo (sección 5 del contrato)."""

        def iso(d: Optional[datetime]) -> Optional[str]:
            return d.isoformat().replace("+00:00", "Z") if d else None

        return {
            "id": self.id,
            "status": self.status.value,
            "progress": round(self.progress, 1),
            "error": self.error,
            "created_at": iso(self.created_at),
            "started_at": iso(self.started_at),
            "finished_at": iso(self.finished_at),
            "request": self.request.to_dict(),
            "metadata": self.request.metadata,
        }
