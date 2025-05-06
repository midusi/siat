from fastapi import APIRouter, Depends, Request
from app.auth.decorators import require_role
from app.services.user_service import UserService
from app.services.dependencies import get_user_service
from app.schemas.user import UserCreateRequest

router = APIRouter(prefix="/admin", tags=["admin"])

@router.post("/user-register")
async def user_register(user_request: UserCreateRequest, service: UserService = Depends(get_user_service)):
    user = service.create(user_request)
    
    return {"user": user}