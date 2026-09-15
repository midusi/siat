from app.schemas.locality import LocalityResponse
from app.domain.entities import Locality
from app.ports.uow import UnitOfWork


class LocalityService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def get_by_id(self, locality_id: int) -> Locality | None:
        return self.uow.localities.get(locality_id)

    def get_list(self) -> list[LocalityResponse]:
        localities = self.uow.localities.list_all()
        return [LocalityResponse.model_validate(l) for l in localities]

    def get_localities_by_district(self, district_id: int) -> list[LocalityResponse]:
        localities = self.uow.localities.list_by_district(district_id)
        return [LocalityResponse.model_validate(l) for l in localities]
