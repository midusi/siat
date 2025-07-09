# crud/task_status_history.py
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import and_, or_
import datetime
from app.models import TaskStatusHistory

def get_current_by_task(db: sessionmaker, task_id: int) -> TaskStatusHistory:
    now = datetime.datetime.now()
    return db.query(TaskStatusHistory).filter(
        TaskStatusHistory.task_id == task_id,
        and_(
            TaskStatusHistory.from_date <= now,
            or_(TaskStatusHistory.to_date == None, TaskStatusHistory.to_date > now)
        )
    ).first()
