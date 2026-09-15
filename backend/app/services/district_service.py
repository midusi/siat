from app.schemas.district import DistrictResponse
from app.ports.uow import UnitOfWork


class DistrictService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def get_list(self, **params) -> list[DistrictResponse]:
        districts = self.uow.districts.list_all(**params)
        return [DistrictResponse.model_validate(d) for d in districts]
