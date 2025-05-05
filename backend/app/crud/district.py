# crud/district.py
from sqlalchemy.orm import Session
from app.models import District
from typing import List

def get_list(db: Session) -> List[District]:
    return db.query(District).all()