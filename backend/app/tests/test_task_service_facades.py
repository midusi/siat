import datetime
from types import SimpleNamespace

import pytest

from app.adapters.persistence.memory import InMemoryUnitOfWork
from app.adapters.storage.memory import InMemoryObjectStorage
from app.domain.exceptions import NotFoundError, ValidationError
from app.schemas.task import FirstFrameInfoResponse, TaskCreateRequest
from app.services.task_service import TaskService
from app.services.video_service import VideoService
from app.tests.test_task_repository import _seed_task

REQUEST = TaskCreateRequest(name="Nueva", locality_id=1, date=datetime.datetime(2026, 1, 1))


@pytest.fixture
def storage():
    return InMemoryObjectStorage(bucket_name="siat-bucket")


@pytest.fixture
def service(storage):
    uow = InMemoryUnitOfWork()
    _seed_task(uow)
    return TaskService(uow, storage)


# --- create_task -----------------------------------------------------------

def test_create_task_with_object_key_uses_the_direct_upload_flow(service, monkeypatch):
    calls = []
    monkeypatch.setattr(service, "create_from_object_key", lambda req, key: calls.append((req, key)) or "created")

    result = service.create_task(REQUEST, object_key="uploads/abc.mp4")

    assert result == "created"
    assert calls == [(REQUEST, "uploads/abc.mp4")]


def test_create_task_with_file_uses_the_traditional_upload_flow(service, monkeypatch):
    file = SimpleNamespace(filename="clip.mp4")
    calls = []
    monkeypatch.setattr(service, "create", lambda req, f: calls.append((req, f)) or "created")

    result = service.create_task(REQUEST, file=file)

    assert result == "created"
    assert calls == [(REQUEST, file)]


def test_create_task_prefers_object_key_over_file(service, monkeypatch):
    monkeypatch.setattr(service, "create_from_object_key", lambda req, key: "from-key")
    monkeypatch.setattr(service, "create", lambda req, f: "from-file")

    result = service.create_task(REQUEST, object_key="uploads/abc.mp4", file=SimpleNamespace(filename="clip.mp4"))

    assert result == "from-key"


@pytest.mark.parametrize("object_key, file", [
    (None, None),
    ("", None),
    (None, SimpleNamespace(filename="")),
    (None, SimpleNamespace(filename=None)),
])
def test_create_task_requires_a_file_or_an_object_key(service, object_key, file):
    with pytest.raises(ValidationError) as error:
        service.create_task(REQUEST, object_key=object_key, file=file)

    assert error.value.status_code == 400
    assert error.value.detail == "Debe proporcionar 'file' o 'object_key'"


# --- get_first_frame_info --------------------------------------------------

def test_get_first_frame_info_combines_frame_and_dimensions(service, monkeypatch):
    monkeypatch.setattr(VideoService, "get_frame", lambda _self, key, index: f"frame:{key}:{index}")

    info = service.get_first_frame_info(1)

    assert info == FirstFrameInfoResponse(
        width=1920, height=1080, image_b64="frame:task/1/clip.mp4:0", mimetype="image/jpeg"
    )


def test_get_first_frame_info_for_missing_task(service):
    with pytest.raises(NotFoundError, match="La tarea no existe"):
        service.get_first_frame_info(999)


# --- get_video_download ----------------------------------------------------

def test_get_video_download_exposes_stream_metadata_and_filename(service, storage):
    storage.upload(b"video-bytes", object_name="task/1/clip.mp4", content_type="video/mp4")

    download = service.get_video_download(1)

    assert b"".join(download.chunks) == b"video-bytes"
    assert download.content_type == "video/mp4"
    assert download.content_length == len(b"video-bytes")
    assert download.filename == "clip.mp4"


def test_get_video_download_for_missing_task(service):
    with pytest.raises(NotFoundError, match="La tarea no existe"):
        service.get_video_download(999)
