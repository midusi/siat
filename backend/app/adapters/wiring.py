from __future__ import annotations

import os

from app.ports.storage import ObjectStorage
from app.ports.uow import UnitOfWork

_DEFAULT_PERSISTENCE = "sql"
_DEFAULT_STORAGE = "minio"


def build_uow(session=None) -> UnitOfWork:
    kind = (os.getenv("PERSISTENCE_ADAPTER") or _DEFAULT_PERSISTENCE).strip().lower()
    if kind == "memory":
        from app.adapters.persistence.memory import InMemoryUnitOfWork
        return InMemoryUnitOfWork()
    if kind in ("sql", "sqlalchemy"):
        from app.adapters.persistence.sqlalchemy_uow import SqlAlchemyUnitOfWork
        if session is None:
            raise ValueError("PERSISTENCE_ADAPTER=sql requiere una sesión de base de datos")
        return SqlAlchemyUnitOfWork(session)
    raise ValueError(
        f"PERSISTENCE_ADAPTER inválido: {kind!r}. Use 'sql' o 'memory'."
    )


def build_object_storage() -> ObjectStorage:
    kind = (os.getenv("STORAGE_ADAPTER") or _DEFAULT_STORAGE).strip().lower()
    if kind == "memory":
        from app.adapters.storage.memory import InMemoryObjectStorage
        bucket = os.getenv("MINIO_BUCKET_NAME") or "siat-bucket"
        return InMemoryObjectStorage(bucket_name=bucket)
    if kind == "minio":
        from app.adapters.storage.minio import MinioObjectStorage
        return MinioObjectStorage.from_env()
    raise ValueError(
        f"STORAGE_ADAPTER inválido: {kind!r}. Use 'minio' o 'memory'."
    )
