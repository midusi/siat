# services/locality_service.py
from sqlalchemy.orm import sessionmaker

from app.crud import locality as locality_crud
from app.schemas.locality import LocalityResponse
from app.models import Locality

class LocalityService:
    def __init__(self, db: sessionmaker):
        self.db = db
        
    def get_by_id(self, locality_id: int) -> Locality:
        return locality_crud.get_by_id(self.db, locality_id)
        
    def get_localities_by_district(self, district_id: int) -> list[LocalityResponse]:
        localities = locality_crud.get_localities_by_district(self.db,district_id)
        return [
            LocalityResponse.model_validate(l) for l in localities
        ]