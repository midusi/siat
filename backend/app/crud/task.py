# crud/task.py
from sqlalchemy.orm import sessionmaker, joinedload
from sqlalchemy.sql import and_, or_, asc
from app.models import Task, TaskStatusHistory, Locality
import datetime

ARCHIVED_STATUS_ID = "ARCHIVED"

def find_all(db: sessionmaker) -> list[Task]:
    now = datetime.datetime.now()
    tasks = (
        db.query(Task)
        .join(Task.status_history)
        .filter(
            and_(
                TaskStatusHistory.from_date <= now,
                or_(TaskStatusHistory.to_date == None, TaskStatusHistory.to_date > now)
            )
        )
        .options(
            joinedload(Task.locality).joinedload(Locality.district),
            joinedload(Task.video),
            joinedload(Task.status_history).joinedload(TaskStatusHistory.task_status),
        )
        .all()
    )
    return tasks

def find_all_active(db: sessionmaker) -> list[Task]:
    """Return tasks whose current status is not ARCHIVED."""
    now = datetime.datetime.now()
    tasks = (
        db.query(Task)
        .join(Task.status_history)
        .filter(
            and_(
                TaskStatusHistory.from_date <= now,
                or_(TaskStatusHistory.to_date == None, TaskStatusHistory.to_date > now)
            ),
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

def find_all_archived(db: sessionmaker) -> list[Task]:
    """Return tasks whose current status is ARCHIVED."""
    now = datetime.datetime.now()
    tasks = (
        db.query(Task)
        .join(Task.status_history)
        .filter(
            and_(
                TaskStatusHistory.from_date <= now,
                or_(TaskStatusHistory.to_date == None, TaskStatusHistory.to_date > now)
            ),
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

def find_by_fields(db: sessionmaker, status_id: str = None) -> list[Task] | None:
    now = datetime.datetime.now()
    
    # Construir las condiciones de filtro dinámicamente
    filter_conditions = [
        TaskStatusHistory.from_date <= now,
        or_(TaskStatusHistory.to_date == None, TaskStatusHistory.to_date > now)
    ]
    
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

def find_one_by_fields(db: sessionmaker, **filters) -> list[Task] | None:
    return db.query(Task).filter_by(**filters).first()


def find_all_by_status(db: sessionmaker, status_id: str) -> list[Task]:
    now = datetime.datetime.now()
    tasks = (
        db.query(Task)
        .join(Task.status_history)
        .filter(
            and_(
                TaskStatusHistory.status_id == status_id,
                TaskStatusHistory.from_date <= now,
                or_(TaskStatusHistory.to_date == None, TaskStatusHistory.to_date > now)
            )
        )
        .all()
    )
    return tasks