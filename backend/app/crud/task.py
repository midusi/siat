# crud/user.py
from sqlalchemy.orm import Session
from app.models import Task

def get_all(db: Session) -> list[Task]:
    return db.query(Task).all()