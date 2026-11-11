from pydantic import BaseModel

class NotificationRequest(BaseModel):
    task_id: int
    status: str
    progress: int | None = None
