from app.schemas.province import ProvinceResponse
from app.schemas.district import DistrictResponse
from app.services.district_service import DistrictService
from app.ports.uow import UnitOfWork


class ProvinceService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow
        self.district_service = DistrictService(uow)

    def get_list(self) -> list[ProvinceResponse]:
        provinces = self.uow.provinces.list_all()
        return [ProvinceResponse.model_validate(p) for p in (provinces or [])]

    def get_districts_by_province(self, province_id: int) -> list[DistrictResponse]:
        return self.district_service.get_list(province_id=province_id)
