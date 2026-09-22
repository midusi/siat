# crud/district.py
from sqlalchemy.orm import Session
from app.models import District

def list_all(db: Session, **filters) -> list[District]:
    return db.query(District).filter_by(**filters).all()