# crud/district.py
from sqlalchemy.orm import Session
from app.models import District

def get_list(db: Session) -> list[District]:
    return db.query(District).all()