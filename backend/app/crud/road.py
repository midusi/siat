# crud/road.py
from sqlalchemy.orm import sessionmaker
from app.models import Road

def find_by_fields(db: sessionmaker, **filters) -> list[Road] | None:
    return db.query(Road).filter_by(**filters).all()

def find_one_by_fields(db: sessionmaker, **filters) -> list[Road] | None:
    return db.query(Road).filter_by(**filters).first()