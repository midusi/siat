# crud/task_status.py
from sqlalchemy.orm import Session
from app.models import TaskStatus

def find_one_by_fields(db: Session, **filters) -> TaskStatus | None:
    return db.query(TaskStatus).filter_by(**filters).first()