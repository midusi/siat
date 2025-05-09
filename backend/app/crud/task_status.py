# crud/task_status.py
from sqlalchemy.orm import Session
from app.models import TaskStatus

def get_by_id(db: Session, task_status_id: int) -> TaskStatus:
    return db.query(TaskStatus).filter(TaskStatus.id == task_status_id).first()
