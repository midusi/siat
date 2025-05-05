# crud/locality.py
from sqlalchemy.orm import Session
from app.models import Locality
from typing import List

def get_localities():
    return [{"id": 1, "name": "Juan"}]

def get_localities_by_district(db: Session, district_id: int):
    return db.query(Locality).filter(Locality.district_id == district_id).all()