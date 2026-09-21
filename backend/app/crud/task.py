# crud/task.py
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.sql import and_, or_, asc
from app.models import Task, TaskStatusHistory, Locality
import datetime

ARCHIVED_STATUS_ID = "ARCHIVED"

def _valid_at(now: datetime.datetime):
    return and_(
        TaskStatusHistory.from_date <= now,
        or_(
            TaskStatusHistory.to_date.is_(None),
            TaskStatusHistory.to_date > now,
        ),
    )

def list_active(db: Session) -> list[Task]:
    """Return tasks whose current status is not ARCHIVED."""
    now = datetime.datetime.now()
    tasks = (
        db.query(Task)
        .join(Task.status_history)
        .filter(
            _valid_at(now),
        )
        .filter(TaskStatusHistory.status_id != ARCHIVED_STATUS_ID)
        .options(
            joinedload(Task.locality).joinedload(Locality.district),
            joinedload(Task.video),
            joinedload(Task.status_history).joinedload(TaskStatusHistory.task_status),
        )
        .all()
    )
    return tasks

def list_archived(db: Session) -> list[Task]:
    """Return tasks whose current status is ARCHIVED."""
    now = datetime.datetime.now()
    tasks = (
        db.query(Task)
        .join(Task.status_history)
        .filter(
            _valid_at(now),
            TaskStatusHistory.status_id == ARCHIVED_STATUS_ID,
        )
        .options(
            joinedload(Task.locality).joinedload(Locality.district),
            joinedload(Task.video),
            joinedload(Task.status_history).joinedload(TaskStatusHistory.task_status),
        )
        .all()
    )
    return tasks

def list_by_status(db: Session, status_id: str) -> list[Task]:
    now = datetime.datetime.now()
    
    # Construir las condiciones de filtro dinámicamente
    filter_conditions = [_valid_at(now)]
    
    if status_id:
        filter_conditions.append(TaskStatusHistory.status_id == status_id)
    
    return (
        db.query(Task)
        .join(Task.status_history)
        .filter(and_(*filter_conditions))
        .order_by(asc(TaskStatusHistory.from_date))
        .options(
            joinedload(Task.locality).joinedload(Locality.district),
            joinedload(Task.video),
            joinedload(Task.status_history).joinedload(TaskStatusHistory.task_status),
        )
        .all()
    )
