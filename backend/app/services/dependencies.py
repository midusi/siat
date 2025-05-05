from fastapi import Depends
from app.db import get_db_session
from sqlalchemy.orm import Session

# Se importan los services
from app.services.locality_service import LocalityService
from app.services.district_service import DistrictService

def get_locality_service(db: Session = Depends(get_db_session)):
    return LocalityService(db)

def get_district_service(db: Session = Depends(get_db_session)):
    return DistrictService(db)