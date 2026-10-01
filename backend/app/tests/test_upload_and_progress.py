import pytest

from app.adapters.persistence.memory import InMemoryUnitOfWork
from app.adapters.storage.memory import InMemoryObjectStorage
from app.domain.exceptions import ValidationError
from app.services import task_upload
from app.services.process_progress import latest_progress
from app.services.task_service import TaskService
from app.services.task_upload import (
    cancel_multipart_upload,
    finish_multipart_upload,
    part_count_for,
    presign_upload_part,
    start_multipart_upload,
)
from app.tests.test_task_repository import _seed_task


def test_part_count_rounds_up():
    assert part_count_for(1, part_size=8) == 1
    assert part_count_for(8, part_size=8) == 1
    assert part_count_for(9, part_size=8) == 2
    assert part_count_for(16, part_size=8) == 2


def test_multipart_rejects_files_over_8gb():
    storage = InMemoryObjectStorage()
    with pytest.raises(ValidationError, match="8 GB"):
        start_multipart_upload(storage, "huge.mp4", "video/mp4", file_size=task_upload.MAX_UPLOAD_BYTES + 1)


def test_part_count_rejects_empty_file():
    with pytest.raises(ValidationError):
        part_count_for(0)


def test_multipart_assembles_parts_in_order(monkeypatch):
    monkeypatch.setattr(task_upload, "PART_SIZE_BYTES", 4)
    storage = InMemoryObjectStorage()
    started = start_multipart_upload(storage, "clip.mp4", "video/mp4", file_size=10)

    assert started["part_count"] == 3
    assert started["part_size"] == 4
    assert started["object_key"].startswith("uploads/")

    storage.put_part(started["object_key"], started["upload_id"], 3, b"cc")
    storage.put_part(started["object_key"], started["upload_id"], 1, b"aaaa")
    storage.put_part(started["object_key"], started["upload_id"], 2, b"bbbb")

    finish_multipart_upload(storage, started["object_key"], started["upload_id"], started["part_count"])

    assert storage._objects[started["object_key"]][0] == b"aaaabbbbcc"


def test_finish_rejects_missing_part(monkeypatch):
    monkeypatch.setattr(task_upload, "PART_SIZE_BYTES", 4)
    storage = InMemoryObjectStorage()
    started = start_multipart_upload(storage, "clip.mp4", "video/mp4", file_size=10)
    storage.put_part(started["object_key"], started["upload_id"], 1, b"aaaa")

    with pytest.raises(ValidationError, match="Faltan partes"):
        finish_multipart_upload(storage, started["object_key"], started["upload_id"], 3)


def test_presign_part_rejects_key_outside_uploads():
    storage = InMemoryObjectStorage()
    with pytest.raises(ValidationError, match="object_key"):
        presign_upload_part(storage, "task/1/clip.mp4", "upload-1", 1)


def test_cancel_then_finish_fails(monkeypatch):
    monkeypatch.setattr(task_upload, "PART_SIZE_BYTES", 4)
    storage = InMemoryObjectStorage()
    started = start_multipart_upload(storage, "clip.mp4", "video/mp4", file_size=4)
    cancel_multipart_upload(storage, started["object_key"], started["upload_id"])

    with pytest.raises(ValidationError, match="cancelada"):
        finish_multipart_upload(storage, started["object_key"], started["upload_id"], 1)


def test_latest_progress_reads_last_percentage():
    text = "inicio\rProgreso: 12% completado (10/100 frames)\rProgreso: 40% completado"
    assert latest_progress(text) == 40
    assert latest_progress("sin datos") is None
    assert latest_progress("Progreso: 250%") == 100
    assert latest_progress("Progreso: 0%") == 0


def test_set_progress_clamps_and_is_listed():
    uow = InMemoryUnitOfWork()
    _seed_task(uow)
    service = TaskService(uow, InMemoryObjectStorage())

    assert service.set_progress(1, 140, commit=True) == 100
    assert service.get_list()[0].progress == 100

    assert service.set_progress(1, -5, commit=True) == 0
    assert service.get_list()[0].progress == 0
