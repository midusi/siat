# crud/road.py
from sqlalchemy.orm import Session
from app.models import Road

def find_by_fields(db: Session, **filters) -> list[Road]:
    return db.query(Road).filter_by(**filters).all()
