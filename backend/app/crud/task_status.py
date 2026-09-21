# crud/task_status.py
from sqlalchemy.orm import Session
from app.models import TaskStatus

def get(db: Session, status_id: str) -> TaskStatus | None:
    return db.query(TaskStatus).filter_by(id=status_id).first()
