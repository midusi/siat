# crud/locality.py
from sqlalchemy.orm import sessionmaker, joinedload
from app.models import Locality

def find_all(db: sessionmaker) -> list[Locality]:
    return db.query(Locality).all()


def get_localities_by_district(db: sessionmaker, district_id: int) -> list[Locality]:
    return db.query(Locality).filter(Locality.district_id == district_id).all()

def find_one_by_fields(db: sessionmaker, **filters) -> Locality:
    return db.query(Locality).filter_by(**filters).first()

def get_localities_by_district2(db: sessionmaker, district_id: int) -> list:
    return (
        db.query(Locality)
        .options(joinedload(Locality.district))
        .filter(Locality.district_id == district_id)
        .all()
    )
