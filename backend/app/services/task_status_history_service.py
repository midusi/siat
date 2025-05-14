# services/task_status_history_service.py
from sqlalchemy.orm import sessionmaker

from app.crud import task_status_history as task_status_history_crud
from app.models import TaskStatus

class TaskStatusHistoryService:
    def __init__(self, db: sessionmaker):
        self.db = db
        
    def get_current_by_task(self, task_id: int) -> TaskStatus:
        return task_status_history_crud.get_current_by_task(self.db, task_id)