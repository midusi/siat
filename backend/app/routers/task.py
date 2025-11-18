from fastapi import APIRouter, Depends, UploadFile, Form, File, HTTPException
# from app.auth.decorators import require_role
from app.services.task_service import TaskService
from app.schemas.task import TaskCreateRequest, TaskConfigRequest, TaskUpdateData
from app.services.dependencies import get_task_service, get_bucket_service
from app.services.bucket_service import BucketService
from datetime import datetime
from fastapi.responses import JSONResponse, Response, StreamingResponse
from app.auth.dependencies import get_current_user, require_role
from pydantic import BaseModel
import hashlib
import time
import os

router = APIRouter(prefix="/task", tags=["task"], dependencies=[Depends(get_current_user)])

# Schemas para presigned URLs
class PresignedUploadRequest(BaseModel):
    filename: str
    content_type: str

class PresignedUploadResponse(BaseModel):
    upload_url: str
    object_key: str
    expires_in: int

@router.post("/upload/presigned-url", response_model=PresignedUploadResponse)
async def get_presigned_upload_url(
    request: PresignedUploadRequest,
    bucket_service: BucketService = Depends(get_bucket_service)
):
    """
    Genera una URL presignada para que el cliente suba archivos directamente a MinIO.
    Esto permite uploads de archivos grandes sin pasar por el servidor backend.
    """
    # Generar object key único
    file_hash = hashlib.sha256(f"{request.filename}{int(time.time())}".encode()).hexdigest()
    file_extension = os.path.splitext(request.filename)[1]
    object_key = f"uploads/{file_hash}{file_extension}"
    
    # Generar URL presignada (expira en 1 hora)
    upload_url = bucket_service.generate_presigned_upload_url(
        object_name=object_key,
        expiration=3600,
        content_type=request.content_type
    )
    
    return PresignedUploadResponse(
        upload_url=upload_url,
        object_key=object_key,
        expires_in=3600
    )

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
    Obtiene los detalles de una tarea desde la base de datos y MinIO.
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
    file: UploadFile = File(None),  # Opcional ahora
    object_key: str = Form(None),  # Nuevo: para upload directo
    service: TaskService = Depends(get_task_service),
    bucket_service: BucketService = Depends(get_bucket_service),
):
    """
    Crea una tarea con un video.
    Dos modos de operación:
    1. Upload tradicional: enviar 'file' (para compatibilidad con código existente)
    2. Upload directo a MinIO: primero usar POST /task/upload/presigned-url,
       subir el archivo a MinIO con la URL presignada, luego llamar este endpoint con 'object_key'
    """
    task_request = TaskCreateRequest(
        name=name,
        locality_id=locality_id,
        date=date
    )
    
    # Modo 1: Upload directo (nuevo método recomendado)
    if object_key:
        # Verificar que el objeto existe en MinIO
        try:
            bucket_service.s3_client.head_object(
                Bucket=bucket_service.BUCKET_NAME,
                Key=object_key
            )
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="El archivo no fue encontrado en el almacenamiento. Asegúrese de subirlo primero usando la URL presignada."
            )
        
        task = service.create_from_object_key(task_request, object_key)
        return {"task": task}
    
    # Modo 2: Upload tradicional (compatibilidad hacia atrás)
    elif file and file.filename:
        task = service.create(task_request, file)
        return {"task": task}
    
    else:
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
    # service.get_first_frame ahora devuelve la cadena en base64
    first_frame_b64 = service.get_first_frame(task_id)
    # Obtener información del video (alto y ancho)
    video_info = service.get_video_dimensions(task_id)  # Debe devolver un dict con 'width' y 'height'

    # Devolvemos un JSON que el frontend puede usar directamente
    return JSONResponse(content={
        "width": video_info.get("width"),
        "height": video_info.get("height"),
        "image_b64": first_frame_b64,
        "mimetype": "image/jpeg"
    })

# NEW: Delete task completely
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