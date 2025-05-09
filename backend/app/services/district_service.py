# services/district_service.py
from fastapi import Depends
from app.db import get_db_session
from sqlalchemy.orm import sessionmaker

from app.crud.district import *
from app.crud import district as district_crud
from app.schemas.district import DistrictResponse

class DistrictService:
    def __init__(self, db: sessionmaker):
        self.db = db
        
    def get_list(self) -> list[DistrictResponse]:
        districts = district_crud.get_list(self.db)
        return [
            DistrictResponse.model_validate(d) for d in districts
        ]