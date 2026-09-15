from __future__ import annotations

import os
from typing import Iterator, Optional, Tuple

from app.domain.exceptions import StorageNotFound


class InMemoryObjectStorage:
    def __init__(self, bucket_name: str = "siat-bucket"):
        self._bucket_name = bucket_name
        self._objects: dict[str, tuple[bytes, str]] = {}

    @property
    def bucket_name(self) -> str:
        return self._bucket_name

    def public_url(self, key: str) -> str:
        return f"/bucket/{self.bucket_name}/{key}"

    def _infer_content_type(self, object_name: str, default: Optional[str] = None) -> str:
        if default:
            return default
        ext = os.path.splitext(object_name)[1].lower()
        if ext == ".json":
            return "application/json"
        if ext in (".mp4", ".m4v"):
            return "video/mp4"
        if ext in (".avi",):
            return "video/x-msvideo"
        if ext in (".mov",):
            return "video/quicktime"
        if ext in (".txt",):
            return "text/plain; charset=utf-8"
        return "application/octet-stream"

    def _read_body(self, data) -> bytes:
        if hasattr(data, "file") and hasattr(getattr(data, "file", None), "read"):
            f = getattr(data, "file", None) or data.file
            try:
                f.seek(0)
            except Exception:
                pass
            body = f.read()
        elif isinstance(data, (bytes, bytearray)):
            body = bytes(data)
        elif isinstance(data, str):
            body = data.encode("utf-8")
        elif hasattr(data, "read") and callable(getattr(data, "read")):
            body = data.read()
        else:
            raise TypeError("Tipo de dato no soportado para upload. Use UploadFile, bytes, str o file-like object.")
        if not isinstance(body, (bytes, bytearray)):
            raise TypeError("El cuerpo a subir debe ser bytes; verifique si intentó usar un método async sin await.")
        return bytes(body)

    def upload(self, data, object_name: str, content_type: Optional[str] = None) -> None:
        body = self._read_body(data)
        ct = self._infer_content_type(object_name, content_type)
        self._objects[object_name] = (body, ct)

    def download(self, path: str, object_name: str) -> None:
        if object_name not in self._objects:
            print(f"Error al descargar el archivo: Objeto no encontrado: {object_name}")
            return
        body, _ = self._objects[object_name]
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "wb") as f:
            f.write(body)

    def delete_object(self, key: str) -> None:
        self._objects.pop(key, None)

    def delete_prefix(self, prefix: str) -> None:
        normalized = prefix.rstrip("/") + "/"
        for key in list(self._objects):
            if key.startswith(normalized):
                del self._objects[key]

    def stream_object(
        self, object_name: str, chunk_size: int = 1024 * 1024
    ) -> Tuple[Iterator[bytes], str, Optional[int]]:
        if object_name not in self._objects:
            raise StorageNotFound(f"Objeto no encontrado: {object_name}")
        body, content_type = self._objects[object_name]

        def iter_chunks():
            for i in range(0, len(body), chunk_size):
                yield body[i : i + chunk_size]

        return iter_chunks(), content_type, len(body)

    def generate_presigned_upload_url(
        self,
        object_name: str,
        expiration: int = 3600,
        content_type: Optional[str] = None,
    ) -> str:
        return f"memory://{self.bucket_name}/{object_name}?expires={expiration}"

    def exists(self, object_name: str) -> bool:
        return object_name in self._objects

    def copy(self, source_key: str, dest_key: str) -> None:
        if source_key not in self._objects:
            raise StorageNotFound(f"Objeto no encontrado: {source_key}")
        self._objects[dest_key] = self._objects[source_key]

    def ensure_bucket(self) -> None:
        return None

    def set_public_read_policy(self) -> None:
        return None
