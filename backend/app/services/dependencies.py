from fastapi import Depends
from app.db import get_db_session
from sqlalchemy.orm import Session

# Se importan los services
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from app.services.locality_service import LocalityService
from app.services.district_service import DistrictService

def get_auth_service(db: Session = Depends(get_db_session)):
    return AuthService(db)

def get_user_service(db: Session = Depends(get_db_session)):
    return UserService(db)

def get_locality_service(db: Session = Depends(get_db_session)):
    return LocalityService(db)

def get_district_service(db: Session = Depends(get_db_session)):
    return DistrictService(db)