# crud/road.py
from sqlalchemy.orm import Session
from app.models import Province

def find_by_fields(db: Session, **filters) -> list[Province]:
    return db.query(Province).filter_by(**filters).all()