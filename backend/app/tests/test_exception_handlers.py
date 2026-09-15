from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.adapters.storage.memory import InMemoryObjectStorage
from app.api.exception_handlers import register_exception_handlers
from app.domain.exceptions import NotFoundError
from app.services.task_upload import presign_upload


def test_app_error_maps_to_http_detail_json():
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/missing")
    def missing():
        raise NotFoundError("La tarea no existe")

    client = TestClient(app)
    response = client.get("/missing")
    assert response.status_code == 404
    assert response.json() == {"detail": "La tarea no existe"}


def test_presign_upload_uses_storage_port():
    storage = InMemoryObjectStorage(bucket_name="siat-bucket")
    result = presign_upload(storage, "clip.mp4", "video/mp4")
    assert result["object_key"].startswith("uploads/")
    assert result["object_key"].endswith(".mp4")
    assert result["expires_in"] == 3600
    assert "siat-bucket" in result["upload_url"]
