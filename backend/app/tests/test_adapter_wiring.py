import pytest

from app.adapters.persistence.memory import InMemoryUnitOfWork
from app.adapters.persistence.sqlalchemy_uow import SqlAlchemyUnitOfWork
from app.adapters.storage.memory import InMemoryObjectStorage
from app.adapters.wiring import build_object_storage, build_uow


def test_persistence_defaults_to_sql(monkeypatch):
    monkeypatch.delenv("PERSISTENCE_ADAPTER", raising=False)
    uow = build_uow(session=object())
    assert isinstance(uow, SqlAlchemyUnitOfWork)


def test_persistence_memory_switch(monkeypatch):
    monkeypatch.setenv("PERSISTENCE_ADAPTER", "memory")
    uow = build_uow()
    assert isinstance(uow, InMemoryUnitOfWork)


def test_persistence_unknown_raises(monkeypatch):
    monkeypatch.setenv("PERSISTENCE_ADAPTER", "oracle")
    with pytest.raises(ValueError, match="PERSISTENCE_ADAPTER"):
        build_uow()


def test_storage_defaults_to_minio(monkeypatch):
    monkeypatch.delenv("STORAGE_ADAPTER", raising=False)

    class FakeMinio:
        @classmethod
        def from_env(cls):
            return cls()

    monkeypatch.setattr("app.adapters.storage.minio.MinioObjectStorage", FakeMinio)
    storage = build_object_storage()
    assert isinstance(storage, FakeMinio)


def test_storage_memory_switch(monkeypatch):
    monkeypatch.setenv("STORAGE_ADAPTER", "memory")
    monkeypatch.setenv("MINIO_BUCKET_NAME", "test-bucket")
    storage = build_object_storage()
    assert isinstance(storage, InMemoryObjectStorage)
    assert storage.bucket_name == "test-bucket"


def test_storage_unknown_raises(monkeypatch):
    monkeypatch.setenv("STORAGE_ADAPTER", "gcs")
    with pytest.raises(ValueError, match="STORAGE_ADAPTER"):
        build_object_storage()
