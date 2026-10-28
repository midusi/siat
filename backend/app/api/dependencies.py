from dataclasses import dataclass
from datetime import datetime

from fastapi import File, Form, Request, UploadFile

from app.config import CSRF_HEADER_NAME
from app.domain.exceptions import ValidationError
from app.schemas.task import TaskCreateRequest

def require_csrf_header(request: Request) -> None:
    if not request.headers.get(CSRF_HEADER_NAME):
        raise ValidationError("CSRF token faltante")


@dataclass
class TaskCreateForm:
    request: TaskCreateRequest
    object_key: str | None
    file: UploadFile | None


def get_task_create_form(
    name: str = Form(...),
    locality_id: int = Form(...),
    date: datetime = Form(...),
    file: UploadFile = File(None),
    object_key: str = Form(None),
) -> TaskCreateForm:
    return TaskCreateForm(
        request=TaskCreateRequest(name=name, locality_id=locality_id, date=date),
        object_key=object_key,
        file=file,
    )
