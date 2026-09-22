# crud/task_status_history.py
from sqlalchemy.orm import Session
from sqlalchemy.sql import and_, or_
import datetime
from app.models import TaskStatusHistory

def get_current(db: Session, task_id: int) -> TaskStatusHistory | None:
    now = datetime.datetime.now()
    return db.query(TaskStatusHistory).filter(
        TaskStatusHistory.task_id == task_id,
        and_(
            TaskStatusHistory.from_date <= now,
            or_(
                TaskStatusHistory.to_date.is_(None),
                TaskStatusHistory.to_date > now,
            ),
        ),
    ).first()
