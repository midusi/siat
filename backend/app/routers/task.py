from fastapi import APIRouter, Depends, UploadFile, Form, File
# from app.auth.decorators import require_role
from app.services.task_service import TaskService
from app.schemas.task import TaskCreateRequest, TaskConfigRequest, TaskUpdateData
from app.services.dependencies import get_task_service
from datetime import datetime
from fastapi.responses import JSONResponse
from app.auth.dependencies import get_current_user, require_role

router = APIRouter(prefix="/task", tags=["task"], dependencies=[Depends(get_current_user)])

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
    file: UploadFile = File(...), 
    service: TaskService = Depends(get_task_service),
):
    # Upload file to MinIO
    if not file.filename:
        raise ValueError("File must be provided")
    task_request = TaskCreateRequest(
        name=name,
        locality_id=locality_id,
        date=date
    )
    task = service.create(task_request, file)
    
    return {"task": task}

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