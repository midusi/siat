from fastapi import APIRouter, Depends, UploadFile, Form, File
from app.auth.decorators import require_role
from app.services.task_service import TaskService
from app.schemas.task import TaskCreateRequest, TaskConfigRequest, TaskUpdateData
from app.services.dependencies import get_task_service, get_bucket_service
from app.services.bucket_service import BucketService
from datetime import datetime

router = APIRouter(prefix="/task", tags=["task"])

@router.get("")
def get_list(service: TaskService = Depends(get_task_service)):
    return service.get_list()

@router.get("/{task_id}")
def get_task(task_id: int, service: TaskService = Depends(get_task_service)):
    """
    Obtiene los detalles de una tarea.
    POR AHORA: Devuelve datos hardcodeados para el desarrollo del frontend.
    A FUTURO: Deberá obtener estos datos de la base de datos o de archivos
             asociados al task_id.
    """
    print(f"Backend: Solicitud recibida para la tarea con ID: {task_id}")

    # Los datos que antes estaban en Svelte, ahora se sirven desde aquí.
    # El backend es ahora la fuente de la verdad.
    hardcoded_task_data = {
        "id": task_id,
        "name": f"Tarea de Prueba #{task_id}",
        "videoPath": f"/video/videoPrueba.mp4",
        "videoWidth": "1920",
        "videoHeight": "1080",
        "videoFps": "30",
        "rutas": {
            "0": {
                "0": { "bicycle": 0, "bus": 0, "car": 0, "heavy_truck": 0, "light_truck": 0, "motorbike": 0 },
                "1": { "bicycle": 0, "bus": 0, "car": 6, "heavy_truck": 0, "light_truck": 0, "motorbike": 0 },
                "2": { "bicycle": 0, "bus": 0, "car": 34, "heavy_truck": 0, "light_truck": 0, "motorbike": 0 },
                "3": { "bicycle": 0, "bus": 0, "car": 8, "heavy_truck": 0, "light_truck": 0, "motorbike": 0 }
            },
            "1": {
                "0": { "bicycle": 0, "bus": 0, "car": 2, "heavy_truck": 0, "light_truck": 0, "motorbike": 0 },
                "1": { "bicycle": 0, "bus": 0, "car": 1, "heavy_truck": 0, "light_truck": 0, "motorbike": 0 },
                "2": { "bicycle": 0, "bus": 0, "car": 19, "heavy_truck": 0, "light_truck": 0, "motorbike": 0 },
                "3": { "bicycle": 0, "bus": 0, "car": 23, "heavy_truck": 0, "light_truck": 1, "motorbike": 1 }
            },
            "2": {
                "0": { "bicycle": 0, "bus": 0, "car": 77, "heavy_truck": 0, "light_truck": 0, "motorbike": 0 },
                "1": { "bicycle": 0, "bus": 0, "car": 11, "heavy_truck": 0, "light_truck": 0, "motorbike": 0 },
                "2": { "bicycle": 0, "bus": 0, "car": 4, "heavy_truck": 0, "light_truck": 0, "motorbike": 0 },
                "3": { "bicycle": 0, "bus": 0, "car": 17, "heavy_truck": 0, "light_truck": 0, "motorbike": 2 }
            },
            "3": {
                "0": { "bicycle": 0, "bus": 0, "car": 8, "heavy_truck": 0, "light_truck": 0, "motorbike": 0 },
                "1": { "bicycle": 0, "bus": 0, "car": 22, "heavy_truck": 0, "light_truck": 0, "motorbike": 0 },
                "2": { "bicycle": 0, "bus": 0, "car": 17, "heavy_truck": 0, "light_truck": 0, "motorbike": 0 },
                "3": { "bicycle": 0, "bus": 0, "car": 0, "heavy_truck": 0, "light_truck": 0, "motorbike": 0 }
            }
        },
        "indeterminados": {
            "1": {
                "frame": "20",
                "class": "car",
                "boundingBox": [
                    "100",
                    "100",
                    "500",
                    "500"
                ],
                "labels": ["0", "IND"],
            },
            "2": {
                "frame": "40",
                "class": "bus",
                "boundingBox": [
                    "200",
                    "200",
                    "600",
                    "600"
                ],
                "labels": ["1", "IND"],
            },
            "3": {
                "frame": "60",
                "class": "motorbike",
                "boundingBox": [
                    "300",
                    "300",
                    "700",
                    "700"
                ],
                "labels": ["IND", "2"],
            },
            "4": {
                "frame": "80",
                "class": "bicycle",
                "boundingBox": [
                    "400",
                    "400",
                    "800",
                    "800"
                ],
                "labels": ["IND", "3"],
            },
            "5": {
                "frame": "100",
                "class": "heavy_truck",
                "boundingBox": [
                    "500",
                    "500",
                    "900",
                    "900"
                ],
                "labels": ["IND", "IND"],
            }
        }
    }

    # Ignoramos el service por ahora y devolvemos directamente el diccionario.
    # FastAPI lo convertirá automáticamente a JSON.
    return hardcoded_task_data
    # return service.get_task(task_id) # Esta línea se usará en el futuro

@router.post("")
async def create(
    name: str = Form(...),
    locality_id: int = Form(...),
    uploaded_at: datetime = Form(...), 
    file: UploadFile = File(...), 
    service: TaskService = Depends(get_task_service),
    bucket_service: BucketService = Depends(get_bucket_service)
):
    # Upload file to MinIO
    if not file.filename:
        raise ValueError("File must be provided")
    task_request = TaskCreateRequest(
        name=name,
        locality_id=locality_id,
        uploaded_at=uploaded_at
    )
    task = service.create(task_request, file)
    bucket_service.upload(
        path=file.file,
        object_name="task/" + str(task.id) + "/" + file.filename
    )
    file.file.close()
    return {"task": task}

@router.post("/{task_id}/config")
async def config(
    task_config_request: TaskConfigRequest,
    task_id: int,
    service: TaskService = Depends(get_task_service)
):
    task = service.config(task_config_request, task_id)
    return {"task": task}

@router.post("/{task_id}/update-data")
async def update_data(task_id: int, updated_data: TaskUpdateData):
    """
    Recibe los datos actualizados de `rutas` e `indeterminados` desde el frontend.
    """
    print(f"Backend: Actualización recibida para la tarea con ID: {task_id}")

    # Ahora puedes acceder a los datos enviados por el frontend
    print("\n--- Data Recibida ---")
    print(updated_data)

    return {"status": "success", "message": f"Task {task_id} data received and processed."}