import hashlib
import os
import time

from app.ports.storage import ObjectStorage


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
