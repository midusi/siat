from sqlalchemy.orm import sessionmaker

from app.crud import province as province_crud
from app.schemas.province import ProvinceResponse
from app.schemas.district import DistrictResponse
from app.services.district_service import DistrictService

class ProvinceService:
    def __init__(self, db: sessionmaker):
        self.db = db
        self.district_service = DistrictService(db)
        
    def get_list(self) -> list[ProvinceResponse]:
        provinces = province_crud.find_by_fields(self.db)
        return [ProvinceResponse.model_validate(p) for p in (provinces or [])]

    def get_districts_by_province(self, province_id: int) -> list[DistrictResponse]:
        return self.district_service.get_list(province_id=province_id)
