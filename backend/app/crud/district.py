# crud/district.py
from sqlalchemy.orm import Session
from app.models import District

def find_by_fields(db: Session, **filters) -> list[District] | None:
    return db.query(District).filter_by(**filters).all()