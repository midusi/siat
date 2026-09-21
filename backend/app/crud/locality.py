# crud/locality.py
from sqlalchemy.orm import Session, joinedload
from app.models import Locality

def list_all(db: Session) -> list[Locality]:
    return db.query(Locality).all()


def list_by_district(db: Session, district_id: int) -> list[Locality]:
    return db.query(Locality).filter(Locality.district_id == district_id).all()

def get(db: Session, locality_id: int) -> Locality | None:
    return db.query(Locality).filter_by(id=locality_id).first()

