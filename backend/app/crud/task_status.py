# crud/task_status.py
from sqlalchemy.orm import sessionmaker
from app.models import TaskStatus

def find_by_fields(db: sessionmaker, **filters) -> list[TaskStatus] | None:
    return db.query(TaskStatus).filter_by(**filters).all()

def find_one_by_fields(db: sessionmaker, **filters) -> list[TaskStatus] | None:
    return db.query(TaskStatus).filter_by(**filters).first()