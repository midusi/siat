# crud/province.py
from sqlalchemy.orm import Session
from app.models import Province

def list_all(db: Session, **filters) -> list[Province]:
    return db.query(Province).filter_by(**filters).all()