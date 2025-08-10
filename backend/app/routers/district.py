# routers/locality.py
from fastapi import APIRouter, Depends, HTTPException
from app.services.locality_service import LocalityService
from app.services.district_service import DistrictService
from app.services.dependencies import get_locality_service, get_district_service
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/district", tags=["district"])

@router.get("/{district_id}/locality")
def get_localities_by_district(district_id: int, service: LocalityService = Depends(get_locality_service), user = Depends(get_current_user)):
    return service.get_localities_by_district(district_id)