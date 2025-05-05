# services/locality_service.py

from app.crud.locality import *
from app.crud import locality as locality_crud
from app.schemas.locality import LocalityResponse

class LocalityService:
    def __init__(self, db: Session):
        self.db = db
        
    def get_localities_by_district(self, district_id: int) -> list[LocalityResponse]:
        localities = locality_crud.get_localities_by_district(self.db,district_id)
        return [
            LocalityResponse.model_validate(l) for l in localities
        ]