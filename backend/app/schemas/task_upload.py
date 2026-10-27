from pydantic import BaseModel

class PresignedUploadRequest(BaseModel):
    filename: str
    content_type: str


class PresignedUploadResponse(BaseModel):
    upload_url: str
    object_key: str
    expires_in: int


class MultipartInitRequest(BaseModel):
    filename: str
    content_type: str = "video/mp4"
    file_size: int


class MultipartInitResponse(BaseModel):
    object_key: str
    upload_id: str
    part_size: int
    part_count: int
    expires_in: int


class MultipartPartRequest(BaseModel):
    object_key: str
    upload_id: str
    part_number: int


class MultipartPartResponse(BaseModel):
    upload_url: str
    part_number: int
    expires_in: int


class MultipartCompleteRequest(BaseModel):
    object_key: str
    upload_id: str
    part_count: int


class MultipartAbortRequest(BaseModel):
    object_key: str
    upload_id: str
