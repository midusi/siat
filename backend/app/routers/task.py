from fastapi import APIRouter, Depends, UploadFile, Form, File
from app.auth.decorators import require_role
from app.services.task_service import TaskService
from app.schemas.task import TaskCreateRequest
from app.services.dependencies import get_task_service
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
    service: TaskService = Depends(get_task_service)
):
    task_request = TaskCreateRequest(
        name=name,
        locality_id=locality_id,
        uploaded_at=uploaded_at
    )
    task = service.create(task_request, file)
    return {"task": task}