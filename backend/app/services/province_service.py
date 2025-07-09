# services/district_service.py
from fastapi import Depends
from app.db import get_db_session
from sqlalchemy.orm import sessionmaker

from app.crud.province import *
from app.crud import province as province_crud
from app.schemas.district import DistrictResponse
from app.services.district_service import DistrictService

class ProvinceService:
    def __init__(self, db: sessionmaker):
        self.db = db
        self.district_service = DistrictService(db)
        
    def get_list(self) -> list[Province]:
        return province_crud.find_by_fields(self.db)

    def get_districts_by_province(self, province_id: int) -> list[DistrictResponse]:
        districts = self.district_service.get_list(province_id=province_id)
        return [
            DistrictResponse.model_validate(d) for d in districts
        ]