import io
from pathlib import Path

import pytest

from app.adapters.storage.memory import InMemoryObjectStorage
from app.domain.exceptions import StorageNotFound
from app.ports.storage import ObjectStorage


def _storage() -> ObjectStorage:
    return InMemoryObjectStorage(bucket_name="siat-bucket")


def test_upload_download_roundtrip(tmp_path: Path):
    storage = _storage()
    storage.upload(b"hello-siat", "task/1/video.mp4", content_type="video/mp4")

    dest = tmp_path / "video.mp4"
    storage.download(str(dest), "task/1/video.mp4")

    assert dest.read_bytes() == b"hello-siat"
    assert storage.exists("task/1/video.mp4")


def test_copy_and_delete():
    storage = _storage()
    storage.upload("payload", "uploads/tmp.mp4")
    storage.copy("uploads/tmp.mp4", "task/9/tmp.mp4")
    storage.delete_object("uploads/tmp.mp4")

    assert storage.exists("task/9/tmp.mp4")
    assert not storage.exists("uploads/tmp.mp4")


def test_delete_prefix():
    storage = _storage()
    storage.upload(b"a", "task/3/a.json")
    storage.upload(b"b", "task/3/b.json")
    storage.upload(b"c", "task/other/c.json")

    storage.delete_prefix("task/3")

    assert not storage.exists("task/3/a.json")
    assert storage.exists("task/other/c.json")


def test_stream_and_presign_and_public_url():
    storage = _storage()
    storage.upload(io.BytesIO(b"xyz"), "task/1/data.json", content_type="application/json")

    gen, content_type, length = storage.stream_object("task/1/data.json")
    assert b"".join(gen) == b"xyz"
    assert content_type == "application/json"
    assert length == 3
    assert storage.public_url("task/1/data.json") == "/bucket/siat-bucket/task/1/data.json"
    assert "task/1/data.json" in storage.generate_presigned_upload_url("task/1/data.json")


def test_stream_missing_raises():
    storage = _storage()
    with pytest.raises(StorageNotFound):
        storage.stream_object("missing.bin")


def test_compat_bucket_service_reexport():
    from app.services.bucket_service import BucketService
    from app.adapters.storage.minio import MinioObjectStorage

    assert BucketService is MinioObjectStorage
