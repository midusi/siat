from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.services.dependencies import get_password_reset_service, get_email_service
from app.services.password_reset_service import PasswordResetService
from app.services.email_service import EmailService

router = APIRouter(prefix="/auth/password", tags=["auth"]) 

class ResetRequest(BaseModel):
    identifier: str  # username or email

class ResetPerform(BaseModel):
    token: str
    new_password: str
    confirm_password: str

@router.post("/request", status_code=204)
async def request_reset(body: ResetRequest, svc: PasswordResetService = Depends(get_password_reset_service), mail: EmailService = Depends(get_email_service)):
    token, to = svc.request_reset_with_email(body.identifier)
    # Always return 204 to avoid user enumeration
    if token:
        subject = "Recuperación de contraseña"
        body_text = f"Usa este token para recuperar tu contraseña (válido por tiempo limitado):\n\n{token}\n"
        mail.send(to or "unknown@local", subject, body_text)
    return {}

@router.post("/perform", status_code=204)
async def perform_reset(body: ResetPerform, svc: PasswordResetService = Depends(get_password_reset_service)):
    ok = svc.perform_reset(body.token, body.new_password, body.confirm_password)
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido o expirado")
    return {}
