# crud/user.py
from sqlalchemy.orm import sessionmaker, joinedload
from sqlalchemy.sql import and_, or_
from app.models import Task, TaskStatusHistory, Locality
import datetime

def get_list(db: sessionmaker) -> list[Task]:
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