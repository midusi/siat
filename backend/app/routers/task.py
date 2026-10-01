from fastapi import APIRouter, Depends, UploadFile, Form, File, HTTPException
from app.services.task_service import TaskService
from app.schemas.task import TaskCreateRequest, TaskConfigRequest, TaskUpdateData
from app.services.dependencies import get_task_service
from datetime import datetime
from fastapi.responses import JSONResponse, Response, StreamingResponse
from app.auth.dependencies import get_current_user, require_role
from pydantic import BaseModel

router = APIRouter(prefix="/task", tags=["task"], dependencies=[Depends(get_current_user)])


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

@router.post("/upload/presigned-url", response_model=PresignedUploadResponse)
async def get_presigned_upload_url(
    request: PresignedUploadRequest,
    service: TaskService = Depends(get_task_service),
):
    """
    Genera una URL presignada para que el cliente suba archivos directamente al object storage.
    Esto permite uploads de archivos grandes sin pasar por el servidor backend.
    """
    result = service.presign_upload(request.filename, request.content_type)
    return PresignedUploadResponse(**result)

@router.post("/upload/multipart/init", response_model=MultipartInitResponse)
async def init_multipart_upload(
    request: MultipartInitRequest,
    service: TaskService = Depends(get_task_service),
):
    """Inicia una subida por partes. El navegador envía cada parte directo al storage."""
    result = service.start_multipart_upload(request.filename, request.content_type, request.file_size)
    return MultipartInitResponse(**result)

@router.post("/upload/multipart/part-url", response_model=MultipartPartResponse)
async def get_multipart_part_url(
    request: MultipartPartRequest,
    service: TaskService = Depends(get_task_service),
):
    result = service.presign_upload_part(request.object_key, request.upload_id, request.part_number)
    return MultipartPartResponse(**result)

@router.post("/upload/multipart/complete")
async def complete_multipart_upload(
    request: MultipartCompleteRequest,
    service: TaskService = Depends(get_task_service),
):
    object_key = service.finish_multipart_upload(
        request.object_key, request.upload_id, request.part_count
    )
    return {"object_key": object_key}

@router.post("/upload/multipart/abort")
async def abort_multipart_upload(
    request: MultipartAbortRequest,
    service: TaskService = Depends(get_task_service),
):
    service.cancel_multipart_upload(request.object_key, request.upload_id)
    return {"status": "aborted"}

@router.get("")
def get_list(service: TaskService = Depends(get_task_service)):
    return service.get_list()

@router.get("/archived")
def get_archived(service: TaskService = Depends(get_task_service)):
    return service.get_archived_list()

@router.post("/{task_id}/archive", dependencies=[Depends(require_role("ROLE_ADMIN", "ROLE_OPERADOR"))])
def archive(task_id: int, service: TaskService = Depends(get_task_service)):
    return service.archive(task_id)

@router.post("/{task_id}/unarchive", dependencies=[Depends(require_role("ROLE_ADMIN", "ROLE_OPERADOR"))])
def unarchive(task_id: int, service: TaskService = Depends(get_task_service)):
    return service.unarchive(task_id)

@router.get("/{task_id}")
def get_task(task_id: int, service: TaskService = Depends(get_task_service)):
    """
    Obtiene los detalles de una tarea desde la base de datos y el object storage.
    Devuelve el path público del video y, si existen, las URLs públicas
    a los archivos JSON de rutas e indeterminados generados por la inferencia.
    """
    print(f"Backend: Solicitud recibida para la tarea con ID: {task_id}")
    return service.get_task(task_id)

@router.post("", dependencies=[Depends(require_role("ROLE_ADMIN", "ROLE_OPERADOR"))])
async def create(
    name: str = Form(...),
    locality_id: int = Form(...),
    date: datetime = Form(...),
    file: UploadFile = File(None),
    object_key: str = Form(None),
    service: TaskService = Depends(get_task_service),
):
    """
    Crea una tarea con un video.
    Dos modos de operación:
    1. Upload tradicional: enviar 'file' (para compatibilidad con código existente)
    2. Upload directo: primero usar POST /task/upload/presigned-url,
       subir el archivo con la URL presignada, luego llamar este endpoint con 'object_key'
    """
    task_request = TaskCreateRequest(
        name=name,
        locality_id=locality_id,
        date=date
    )

    if object_key:
        task = service.create_from_object_key(task_request, object_key)
        return {"task": task}

    if file and file.filename:
        task = service.create(task_request, file)
        return {"task": task}

    raise HTTPException(
        status_code=400,
        detail="Debe proporcionar 'file' o 'object_key'"
    )

@router.post("/{task_id}/config", dependencies=[Depends(require_role("ROLE_ADMIN", "ROLE_OPERADOR"))])
async def config(
    task_id: int,
    task_config_request: TaskConfigRequest,
    service: TaskService = Depends(get_task_service),
):
    print(f"Configurar tarea {task_id} con datos:", task_config_request)
    task = service.config(task_config_request, task_id)
    return {"task": task}

@router.post("/{task_id}/update-data", dependencies=[Depends(require_role("ROLE_ADMIN", "ROLE_OPERADOR"))])
async def update_data(
    task_id: int,
    updated_data: TaskUpdateData,
    service: TaskService = Depends(get_task_service),
):
    """
    Recibe los datos actualizados de `rutas` e `indeterminados` desde el frontend y
    actualiza los archivos correspondientes en el bucket para mantener consistencia.
    """
    print(f"Backend: Actualización recibida para la tarea con ID: {task_id}")
    result = service.update_data(task_id, updated_data)
    return {"status": "success", **result}

@router.get("/{task_id}/get-first-frame-info")
async def get_first_frame_info(task_id: int, service: TaskService = Depends(get_task_service)):
    first_frame_b64 = service.get_first_frame(task_id)
    video_info = service.get_video_dimensions(task_id)

    return JSONResponse(content={
        "width": video_info.get("width"),
        "height": video_info.get("height"),
        "image_b64": first_frame_b64,
        "mimetype": "image/jpeg"
    })

@router.delete("/{task_id}", dependencies=[Depends(require_role("ROLE_ADMIN", "ROLE_OPERADOR"))], status_code=204)
def delete_task(task_id: int, service: TaskService = Depends(get_task_service)):
    service.delete(task_id)
    return Response(status_code=204)

@router.get("/{task_id}/download", dependencies=[Depends(require_role("ROLE_ADMIN", "ROLE_OPERADOR"))])
def download_video(task_id: int, service: TaskService = Depends(get_task_service)):
    """Devuelve el video asociado a la tarea como descarga (streaming completo).
    Si existe un video procesado se prioriza. (No implementa Range)."""
    video_key, filename = service.get_video_download_info(task_id)
    gen, content_type, content_length = service.video_service.get_video_stream(video_key)
    headers = {'Content-Disposition': f'attachment; filename="{filename}"'}
    if content_length:
        headers['Content-Length'] = str(content_length)
    return StreamingResponse(gen, media_type=content_type, headers=headers)
