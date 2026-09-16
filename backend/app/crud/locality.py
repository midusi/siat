# crud/locality.py
from sqlalchemy.orm import Session, joinedload
from app.models import Locality

def find_all(db: Session) -> list[Locality]:
    return db.query(Locality).all()


def get_localities_by_district(db: Session, district_id: int) -> list[Locality]:
    return db.query(Locality).filter(Locality.district_id == district_id).all()

def find_one_by_fields( db: Session, **filters) -> Locality | None:
    return db.query(Locality).filter_by(**filters).first()

