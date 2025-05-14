# crud/route.py
from sqlalchemy.orm import sessionmaker
from app.models import Route

def find_by_fields(db: sessionmaker, **filters) -> list[Route] | None:
    return db.query(Route).filter_by(**filters).all()

def find_one_by_fields(db: sessionmaker, **filters) -> Route | None:
    return db.query(Route).filter_by(**filters).first()