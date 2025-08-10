# routers/locality.py
from fastapi import APIRouter, Depends
from app.services.province_service import ProvinceService
from app.services.dependencies import get_province_service
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/province", tags=["province"]) 

@router.get("")
def get_list(service: ProvinceService = Depends(get_province_service), user = Depends(get_current_user)):
    return service.get_list()

@router.get("/{province_id}/district")
def get_districts_by_province(province_id: int, service: ProvinceService = Depends(get_province_service), user = Depends(get_current_user)):
    return service.get_districts_by_province(province_id)
