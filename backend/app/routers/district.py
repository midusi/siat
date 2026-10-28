from fastapi import APIRouter, Depends
from app.services.locality_service import LocalityService
from app.services.dependencies import get_locality_service
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/district", tags=["district"], dependencies=[Depends(get_current_user)])

@router.get("/{district_id}/locality")
def get_localities_by_district(district_id: int, service: LocalityService = Depends(get_locality_service)):
    return service.get_localities_by_district(district_id)
