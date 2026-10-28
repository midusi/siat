from fastapi import APIRouter, Depends
from app.schemas.auth import ResetPerform, ResetRequest
from app.services.dependencies import get_password_reset_service
from app.services.password_reset_service import PasswordResetService

router = APIRouter(prefix="/auth/password", tags=["auth"])

@router.post("/request", status_code=204)
async def request_reset(body: ResetRequest, svc: PasswordResetService = Depends(get_password_reset_service)):
    # Always 204, exista o no el usuario, para evitar enumeración
    svc.request_reset(body.identifier)
    return {}

@router.post("/perform", status_code=204)
async def perform_reset(body: ResetPerform, svc: PasswordResetService = Depends(get_password_reset_service)):
    svc.perform_reset(body.token, body.new_password, body.confirm_password)
    return {}
