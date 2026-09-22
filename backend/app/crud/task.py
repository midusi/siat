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

def _valid_tasks_query(db: Session, now: datetime.datetime):
    return (
        db.query(Task)
        .join(Task.status_history)
        .filter(_valid_at(now))
        .options(
            joinedload(Task.locality).joinedload(Locality.district),
            joinedload(Task.video),
            joinedload(Task.status_history).joinedload(TaskStatusHistory.task_status),
        )
    )

def list_active(db: Session) -> list[Task]:
    """Return tasks whose current status is not ARCHIVED."""
    now = datetime.datetime.now()
    return (
        _valid_tasks_query(db, now)
        .filter(TaskStatusHistory.status_id != ARCHIVED_STATUS_ID)
        .all()
    )

def list_archived(db: Session) -> list[Task]:
    """Return tasks whose current status is ARCHIVED."""
    now = datetime.datetime.now()
    return (
        _valid_tasks_query(db, now)
        .filter(TaskStatusHistory.status_id == ARCHIVED_STATUS_ID)
        .all()
    )

def list_by_status(db: Session, status_id: str) -> list[Task]:
    now = datetime.datetime.now()
    query = _valid_tasks_query(db, now)
    if status_id:
        query = query.filter(TaskStatusHistory.status_id == status_id)
    return query.order_by(asc(TaskStatusHistory.from_date)).all()
