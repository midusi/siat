# crud/road.py
from sqlalchemy.orm import sessionmaker
from app.models import Province

def find_by_fields(db: sessionmaker, **filters) -> list[Province] | None:
    return db.query(Province).filter_by(**filters).all()