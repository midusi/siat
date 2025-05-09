# crud/locality.py
from sqlalchemy.orm import Session, joinedload
from app.models import Locality

def get_localities_by_district(db: Session, district_id: int) -> list[Locality]:
    return db.query(Locality).filter(Locality.district_id == district_id).all()

def get_by_id(db: Session, locality_id: int) -> Locality:
    return db.query(Locality).filter(Locality.id == locality_id).first()

def get_localities_by_district2(db: Session, district_id: int) -> list:
    return (
        db.query(Locality)
        .options(joinedload(Locality.district))
        .filter(Locality.district_id == district_id)
        .all()
    )
