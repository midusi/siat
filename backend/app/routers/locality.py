from fastapi import APIRouter, Depends
from app.services.locality_service import LocalityService
from app.services.dependencies import get_locality_service

router = APIRouter(prefix="/locality", tags=["locality"])

@router.get("")
def get_all(service: LocalityService = Depends(get_locality_service)):
    return service.get_list()
