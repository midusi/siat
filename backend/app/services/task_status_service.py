# services/task_status_service.py
from sqlalchemy.orm import sessionmaker

from app.crud import task_status as task_status_crud
from app.models import TaskStatus

class TaskStatusService:
    def __init__(self, db: sessionmaker):
        self.db = db
        
    def get_by_id(self, task_status_id: str) -> TaskStatus:
        return task_status_crud.get_by_id(self.db, task_status_id)