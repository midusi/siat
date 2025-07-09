from fastapi import APIRouter, Depends, UploadFile, Form, File
from app.auth.decorators import require_role
from app.services.task_service import TaskService
from app.schemas.task import TaskCreateRequest, TaskConfigRequest
from app.services.dependencies import get_task_service, get_bucket_service
from app.services.bucket_service import BucketService
from datetime import datetime

router = APIRouter(prefix="/task", tags=["task"])

@router.get("")
def get_list(service: TaskService = Depends(get_task_service)):
    return service.get_list()

@router.get("/{task_id}")
def get_task(task_id: int, service: TaskService = Depends(get_task_service)):
    return service.get_task(task_id)

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