import hashlib
import os
import time

from app.domain.exceptions import StorageNotFound, ValidationError
from app.ports.storage import ObjectStorage

# Cada parte queda por debajo de los límites habituales de proxy (cuerpo y timeout).
# S3/MinIO exigen que toda parte excepto la última mida al menos 5 MB.
PART_SIZE_BYTES = 5 * 1024 * 1024
MAX_UPLOAD_BYTES = 8 * 1024 * 1024 * 1024


def presign_upload(
    storage: ObjectStorage,
    filename: str,
    content_type: str,
    expiration: int = 3600,
) -> dict:
    file_hash = hashlib.sha256(f"{filename}{int(time.time())}".encode()).hexdigest()
    file_extension = os.path.splitext(filename)[1]
    object_key = f"uploads/{file_hash}{file_extension}"
    upload_url = storage.generate_presigned_upload_url(
        object_name=object_key,
        expiration=expiration,
        content_type=content_type,
    )
    return {
        "upload_url": upload_url,
        "object_key": object_key,
        "expires_in": expiration,
    }


def part_count_for(file_size: int, part_size: int = PART_SIZE_BYTES) -> int:
    if file_size <= 0:
        raise ValidationError("El archivo está vacío")
    if part_size <= 0:
        raise ValidationError("Tamaño de parte inválido")
    return (file_size + part_size - 1) // part_size


def _staging_key(filename: str) -> str:
    file_hash = hashlib.sha256(f"{filename}{int(time.time())}".encode()).hexdigest()
    file_extension = os.path.splitext(filename)[1]
    return f"uploads/{file_hash}{file_extension}"


def assert_staging_key(object_key: str) -> None:
    if (
        not object_key.startswith("uploads/")
        or ".." in object_key
        or object_key.startswith("/")
        or "\\" in object_key
    ):
        raise ValidationError("object_key inválido")


def start_multipart_upload(
    storage: ObjectStorage,
    filename: str,
    content_type: str,
    file_size: int,
    expiration: int = 3600,
) -> dict:
    if file_size > MAX_UPLOAD_BYTES:
        raise ValidationError("El archivo supera el tamaño máximo de 8 GB")
    part_size = PART_SIZE_BYTES
    part_count = part_count_for(file_size, part_size)
    object_key = _staging_key(filename)
    upload_id = storage.create_multipart_upload(object_key, content_type or None)
    return {
        "object_key": object_key,
        "upload_id": upload_id,
        "part_size": part_size,
        "part_count": part_count,
        "expires_in": expiration,
    }


def presign_upload_part(
    storage: ObjectStorage,
    object_key: str,
    upload_id: str,
    part_number: int,
    expiration: int = 3600,
) -> dict:
    assert_staging_key(object_key)
    if part_number < 1:
        raise ValidationError("part_number inválido")
    try:
        upload_url = storage.generate_presigned_part_url(
            object_name=object_key,
            upload_id=upload_id,
            part_number=part_number,
            expiration=expiration,
        )
    except StorageNotFound:
        raise ValidationError("La subida no existe o fue cancelada")
    return {"upload_url": upload_url, "part_number": part_number, "expires_in": expiration}


def finish_multipart_upload(
    storage: ObjectStorage,
    object_key: str,
    upload_id: str,
    part_count: int,
) -> str:
    assert_staging_key(object_key)
    if part_count < 1:
        raise ValidationError("part_count inválido")
    try:
        parts = storage.list_uploaded_parts(object_key, upload_id)
    except StorageNotFound:
        raise ValidationError("La subida no existe o fue cancelada")
    numbers = sorted(part["PartNumber"] for part in parts)
    expected = list(range(1, part_count + 1))
    if numbers != expected:
        raise ValidationError(
            f"Faltan partes del video ({len(numbers)} de {part_count}). Reintentá la subida."
        )
    ordered = sorted(parts, key=lambda part: part["PartNumber"])
    storage.complete_multipart_upload(object_key, upload_id, ordered)
    return object_key


def cancel_multipart_upload(storage: ObjectStorage, object_key: str, upload_id: str) -> None:
    assert_staging_key(object_key)
    storage.abort_multipart_upload(object_key, upload_id)
