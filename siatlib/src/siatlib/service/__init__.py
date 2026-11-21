"""
siatlib.service — siatlib como servicio de inferencia con cola y estados.

Uso desde Python (sin HTTP):

    from siatlib.service import JobStore, JobRequest, ServiceSettings, Worker

    settings = ServiceSettings(data_dir=Path("data"), models_dir=Path("models"))
    store = JobStore(settings.db_path)
    job = store.create(JobRequest.from_dict({...}))
    Worker(store, settings).start()

La API HTTP (FastAPI) está en `siatlib.service.api` y requiere el extra:
`pip install siatlib[service]`. Contrato: docs/SIATLIB_SERVICE_API.md
"""

from .config import ServiceSettings
from .jobs import (
    InvalidJobRequest,
    InvalidTransition,
    Job,
    JobOptions,
    JobRequest,
    JobStatus,
    ZoneSpec,
)
from .store import JobNotFound, JobStore
from .worker import Worker

__all__ = [
    "ServiceSettings",
    "InvalidJobRequest",
    "InvalidTransition",
    "Job",
    "JobOptions",
    "JobRequest",
    "JobStatus",
    "ZoneSpec",
    "JobNotFound",
    "JobStore",
    "Worker",
]
