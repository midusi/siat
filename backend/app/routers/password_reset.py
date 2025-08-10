from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.services.dependencies import get_password_reset_service, get_email_service
from app.services.password_reset_service import PasswordResetService
from app.services.email_service import EmailService
from app.crud import user as user_crud
from app.db import SessionLocal

router = APIRouter(prefix="/auth/password", tags=["auth"]) 

class ResetRequest(BaseModel):
    identifier: str  # username or email

class ResetPerform(BaseModel):
    token: str
    new_password: str
    confirm_password: str

@router.post("/request", status_code=204)
async def request_reset(body: ResetRequest, svc: PasswordResetService = Depends(get_password_reset_service), mail: EmailService = Depends(get_email_service)):
    token = svc.request_reset(body.identifier)
    # Always return 204 to avoid user enumeration
    if token:
        # In a real app, build a frontend link: e.g. https://app/reset?token=...
        # Send to the user's email (we fetch silently here)
        db = SessionLocal()
        try:
            user = user_crud.find_one_by_fields(db, username=body.identifier) or user_crud.find_one_by_fields(db, email=body.identifier)
            to = user.email if user else ""
        finally:
            db.close()
        subject = "Recuperación de contraseña"
        body_text = f"Usa este token para recuperar tu contraseña (válido por tiempo limitado):\n\n{token}\n"
        if to:
            mail.send(to, subject, body_text)
        else:
            mail.send("unknown@local", subject, body_text)
    return {}

@router.post("/perform", status_code=204)
async def perform_reset(body: ResetPerform, svc: PasswordResetService = Depends(get_password_reset_service)):
    ok = svc.perform_reset(body.token, body.new_password, body.confirm_password)
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido o expirado")
    return {}
