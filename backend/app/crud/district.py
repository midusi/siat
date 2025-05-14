# crud/district.py
from sqlalchemy.orm import sessionmaker
from app.models import District

def get_list(db: sessionmaker) -> list[District]:
    return db.query(District).all()