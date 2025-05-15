# crud/district.py
from sqlalchemy.orm import sessionmaker
from app.models import District

def find_by_fields(db: sessionmaker, **filters) -> list[District] | None:
    return db.query(District).filter_by(**filters).all()