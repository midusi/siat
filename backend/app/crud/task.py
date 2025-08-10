# crud/task.py
from sqlalchemy.orm import sessionmaker, joinedload
from sqlalchemy.sql import and_, or_
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

def find_by_fields(db: sessionmaker, **filters) -> list[Task]:
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

def find_one_by_fields(db: sessionmaker, **filters) -> list[Task] | None:
    return db.query(Task).filter_by(**filters).first()