# routers/locality.py
from fastapi import APIRouter, Depends, HTTPException
from app.services.locality_service import LocalityService
from app.services.district_service import DistrictService
from app.services.dependencies import get_locality_service, get_district_service

router = APIRouter(prefix="/district", tags=["district"])

@router.get("")
def get_localities_by_district(service: DistrictService = Depends(get_district_service)):
    return service.get_list()

@router.get("/{district_id}/locality")
def get_localities_by_district(district_id: int, service: LocalityService = Depends(get_locality_service)):
    return service.get_localities_by_district(district_id)

@router.get("/{district_id}/locality2")
def get_localities_by_district(district_id: int, service: LocalityService = Depends(get_locality_service)):
    return service.get_localities_by_district2(district_id)